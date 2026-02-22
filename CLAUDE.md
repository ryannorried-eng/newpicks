# SharpPicks — Claude Code Build Prompt

You are building a sports betting analytics app called **SharpPicks** from scratch in `/Users/ryannorried/sharppicks/`. Follow the architecture document below precisely, implementing phase by phase. After completing each phase, run the verification step before moving on.

---

## Context

Build a greenfield sports betting analytics app. The goal: identify a few sharp picks per day (moneyline, spread, totals) across NBA, NFL, MLB, NHL, then automatically construct correlation-aware parlays at different risk tiers. The system prioritizes signal quality over quantity — fewer, sharper picks that hit at a high rate.

Tech stack: Python/FastAPI backend + React/Vite frontend + PostgreSQL, all via Docker Compose.

---

## CRITICAL TWEAKS (Apply these throughout — they override the base plan where they conflict)

### Tweak 1: Adaptive Odds Polling (replaces "4 fetches/day/sport")

Steam move detection ("3+ books move within 30 min") requires intra-hour sampling during active windows. With 4/day you'll miss most movement patterns.

**Implementation:**
- Off-hours (no games within 6 hours): 1–2 pulls/day per sport
- Pre-game window (3 hours before first game): every 15 minutes, only for sports with games today
- Active game window (games in progress): every 10 minutes, only active sports
- Only poll top 8 books during high-frequency windows to conserve quota
- Store only deltas: if odds haven't changed for a game/book/market since last snapshot, skip the insert
- Track API quota via `x-requests-remaining` header and auto-throttle if below 50 remaining
- Budget target: stay under 500 req/month (free tier) by being smart about when and what to poll

Create `backend/app/services/polling_scheduler.py` that implements this adaptive logic. The scheduler should:
- Check today's game schedule at startup and every hour
- Compute polling windows dynamically
- Expose a `/api/v1/system/polling-status` endpoint showing current mode, quota remaining, next poll time

### Tweak 2: Odds Snapshots — Indexing, Partitioning, Deduplication

This table will be your largest and your bottleneck if not handled early.

**Required compound indexes on odds_snapshots:**
```sql
CREATE INDEX ix_odds_sport_commence ON odds_snapshots (sport_key, commence_time);
CREATE INDEX ix_odds_game_market_time ON odds_snapshots (game_id, market, snapshot_time);
CREATE INDEX ix_odds_book_market_time ON odds_snapshots (bookmaker, market, snapshot_time);
CREATE INDEX ix_odds_game_book_market_side ON odds_snapshots (game_id, bookmaker, market, side, snapshot_time);
```

**Uniqueness guard:** Add a unique constraint on `(game_id, bookmaker, market, side, snapshot_time_rounded)` where `snapshot_time_rounded` is truncated to the nearest minute. This prevents duplicate inserts from overlapping polls.

**Delta-only inserts:** Before inserting a snapshot, check if the most recent snapshot for the same `(game_id, bookmaker, market, side)` has identical odds. If so, skip the insert. This dramatically reduces table size.

**Future-proof:** Add a comment in the migration noting that daily partitioning by `snapshot_time` (Postgres native range partitioning) should be implemented once the table exceeds 1M rows.

### Tweak 3: Explicit EV Calculation — Consensus vs Best Line (not "model probability")

Be very precise about the EV calculation. Do NOT call the consensus probability a "model probability" — that term is reserved for when real ML modeling is added later.

**The correct framing:**
```
consensus_fair_prob = average no-vig probability across all bookmakers (this is the "fair" price)
best_available_odds = best line you can actually take at any single book
EV% = (consensus_fair_prob × decimal(best_available_odds)) - 1
```

This is a market-efficiency arbitrage approach: "the market collectively says this should be priced at X, but Book Y is offering X+2%." That's a real, coherent edge.

**In code:**
- Name the variable `consensus_prob` or `fair_prob`, never `model_prob` (until Phase 5 when actual modeling is added)
- The pick schema should have fields: `fair_prob`, `best_odds`, `best_book`, `ev_pct`
- Add a `prob_source` field to picks: either `"consensus"` or `"model_v1"` etc. — so you always know where the probability came from

### Tweak 4: Parlay Compatibility Matrix & Hard Blocks

In Phase 3, before correlation scoring, add a compatibility layer:

**Hard blocks (never combine):**
- Same game + same market (e.g., Team A spread + Team A moneyline in same game)
- Same game + same side of related markets (e.g., Team A ML + Team A spread — these are ~0.90 correlated, essentially the same bet)
- Any two legs where correlation > 0.85 in the Conservative tier

**Compatibility matrix** `backend/app/analytics/compatibility.py`:
```python
def check_compatibility(leg_a, leg_b, risk_level) -> tuple[bool, str]:
    """Returns (is_compatible, reason) for a pair of legs."""
    # Same game checks
    # Same team checks
    # Correlation ceiling per risk level:
    #   Conservative: max correlation 0.15
    #   Moderate: max correlation 0.40
    #   Aggressive: max correlation 0.70
```

**Structural correlations to encode as priors:**
- Same-game ML + spread (same team): +0.90 → BLOCKED
- Same-game ML winner + game over: +0.25 to +0.35
- Same-game ML winner + game under: -0.15 to -0.25
- Same-game spread cover + over: +0.10 to +0.20
- Cross-game, same sport, same day: ~0.00 to +0.05
- Cross-sport: 0.00

### Tweak 5: Precise Closing Line & Dual CLV

**Closing line definition:**
- "Closing snapshot" = the last odds snapshot where `snapshot_time <= game.commence_time - interval '1 minute'`
- If no snapshot exists within 2 hours of game start, mark CLV as `null` (insufficient data)

**Dual CLV calculation:**
```python
# Market CLV: did we beat the consensus close?
market_clv = closing_consensus_implied_prob - pick_implied_prob_at_time_of_pick

# Book CLV: did we beat the closing line at the same book?
book_clv = closing_book_implied_prob - pick_implied_prob_at_time_of_pick
```

Store BOTH on the pick record. Market CLV is the gold standard for measuring sharpness. Book CLV matters for practical profitability.

Add fields to the `picks` table:
- `closing_consensus_prob` (FLOAT, nullable)
- `closing_book_prob` (FLOAT, nullable)  
- `market_clv` (FLOAT, nullable)
- `book_clv` (FLOAT, nullable)

### Tweak 6: Idempotent, Lock-Safe Scheduled Tasks

Every scheduled task must be stateless and idempotent to prevent double-ingestion if multiple instances run.

**Pattern for every task:**
```python
async def task_name(session: AsyncSession):
    # 1. Acquire Postgres advisory lock (hash of task name)
    lock_id = hash("task_name") & 0x7FFFFFFF
    result = await session.execute(text(f"SELECT pg_try_advisory_lock({lock_id})"))
    if not result.scalar():
        logger.info("Another instance running, skipping")
        return
    try:
        # 2. Use upserts with deterministic keys (not blind inserts)
        # 3. Do work
        pass
    finally:
        await session.execute(text(f"SELECT pg_advisory_unlock({lock_id})"))
```

Additionally, separate scheduled tasks into a `worker` process in Docker Compose:
```yaml
worker:
  build: ./backend
  command: python -m app.worker  # runs scheduler only
  depends_on: [db]
  env_file: ./backend/.env
```

This way the API server and the task worker are separate containers. The API serves requests; the worker runs cron jobs. No collision.

### Tweak 7: MVP UI Scope — Phased Frontend

**Phase 4A (build first):**
- Dashboard (today's picks + today's parlays)
- Picks page (filterable table with signal breakdown)
- Odds page (cross-book comparison + line movement chart)

**Phase 4B (build second):**
- Parlays page (pre-built + interactive builder)

**Phase 4C (build last, read-only initially):**
- Performance page (charts only, no forms)
- Bankroll page (read-only balance + chart, no deposit/withdraw forms until settlement is stable and trusted)

### Tweak 8: Data Quality Layer (NEW — add this)

Create `backend/app/analytics/data_quality.py` — a first-class concept that gates confidence scoring.

**Data quality signals per game:**
```python
@dataclass
class DataQuality:
    books_covered: int              # How many books have odds for this game
    snapshot_freshness_minutes: int  # Minutes since last odds update
    sharp_books_present: bool       # Are Pinnacle/Circa/Bookmaker in the data?
    line_dispersion: float          # Std dev of no-vig probs across books (lower = tighter consensus)
    market_completeness: float      # % of markets (h2h, spreads, totals) with data
```

**Integration with confidence tiers:**
- If `books_covered < 4`: cap confidence at MEDIUM max
- If `snapshot_freshness_minutes > 120`: cap confidence at LOW max  
- If `sharp_books_present == False`: reduce composite score by 0.10
- If `line_dispersion > 0.06` (6% spread): flag as "thin market" and reduce confidence
- If `market_completeness < 0.66`: flag as incomplete data

This prevents a single outlier book from generating a fake "high confidence" pick.

### Tweak 9: CLV Tracking from Day One

Do NOT wait until Phase 5 to capture closing lines. Start logging them in Phase 1 the moment odds are flowing.

In `tasks/fetch_odds.py`, after every odds fetch:
- For any game where `commence_time` has passed, mark the most recent prior snapshot as `is_closing = True`
- This is just a flag — zero computation cost, but you can never go back in time to get this data

In the `odds_snapshots` table, add:
- `is_closing` (BOOLEAN, default False)

### Tweak 10: Kelly Sizing in Phase 3 (not Phase 5)

Every pick and parlay should come with a Kelly-based unit suggestion from the moment picks are generated.

In `backend/app/utils/odds_math.py`:
```python
def kelly_criterion(fair_prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """Quarter-Kelly by default. Returns fraction of bankroll to wager."""
    b = decimal_odds - 1
    q = 1 - fair_prob
    full_kelly = (b * fair_prob - q) / b
    return max(0, full_kelly * fraction)
```

Add to pick and parlay response schemas:
- `suggested_kelly_fraction` (FLOAT)
- `suggested_units` (FLOAT) — based on current bankroll if set, otherwise as fraction

---

## Phase 1: Foundation — Project Setup, Data Pipeline, Database

### 1A: Project Scaffolding

Create the full directory structure:

```
sharppicks/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, CORS, lifespan
│   │   ├── config.py            # Pydantic BaseSettings (.env loading)
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── worker.py            # Standalone scheduler process (Tweak 6)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py        # Aggregates all route modules
│   │   │       ├── picks.py
│   │   │       ├── parlays.py
│   │   │       ├── odds.py
│   │   │       ├── games.py
│   │   │       ├── performance.py
│   │   │       ├── bankroll.py
│   │   │       ├── sports.py
│   │   │       └── system.py        # Polling status, health check
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── sport.py
│   │   │   ├── team.py
│   │   │   ├── game.py
│   │   │   ├── odds_snapshot.py
│   │   │   ├── game_stat.py
│   │   │   ├── pick.py
│   │   │   ├── parlay.py
│   │   │   ├── bankroll.py
│   │   │   └── performance.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── picks.py
│   │   │   ├── parlays.py
│   │   │   ├── odds.py
│   │   │   ├── games.py
│   │   │   ├── performance.py
│   │   │   └── bankroll.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pick_service.py
│   │   │   ├── parlay_service.py
│   │   │   ├── performance_service.py
│   │   │   ├── bankroll_service.py
│   │   │   └── polling_scheduler.py   # Adaptive polling (Tweak 1)
│   │   ├── analytics/
│   │   │   ├── __init__.py
│   │   │   ├── ev_calculator.py
│   │   │   ├── line_movement.py
│   │   │   ├── consensus.py
│   │   │   ├── sharp_signals.py
│   │   │   ├── confidence.py
│   │   │   ├── correlation.py
│   │   │   ├── compatibility.py       # Parlay hard blocks (Tweak 4)
│   │   │   └── data_quality.py        # Data quality layer (Tweak 8)
│   │   ├── data_providers/
│   │   │   ├── __init__.py
│   │   │   ├── odds_api.py
│   │   │   ├── balldontlie.py
│   │   │   └── rate_limiter.py
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── fetch_odds.py          # Includes is_closing flagging (Tweak 9)
│   │   │   ├── fetch_scores.py
│   │   │   ├── fetch_stats.py
│   │   │   ├── generate_picks.py
│   │   │   └── settle_picks.py        # Dual CLV calculation (Tweak 5)
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── odds_math.py           # Includes kelly_criterion (Tweak 10)
│   │       ├── constants.py
│   │       └── exceptions.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_odds_math.py
│   │   ├── test_ev_calculator.py
│   │   └── test_data_quality.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── picks.ts
│   │   │   ├── parlays.ts
│   │   │   ├── odds.ts
│   │   │   ├── games.ts
│   │   │   ├── performance.ts
│   │   │   └── bankroll.ts
│   │   ├── components/
│   │   │   ├── picks/
│   │   │   ├── parlays/
│   │   │   ├── odds/
│   │   │   ├── performance/
│   │   │   ├── bankroll/
│   │   │   ├── layout/
│   │   │   └── common/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Picks.tsx
│   │   │   ├── Parlays.tsx
│   │   │   ├── Odds.tsx
│   │   │   ├── Performance.tsx
│   │   │   └── Bankroll.tsx
│   │   ├── hooks/
│   │   │   ├── usePicks.ts
│   │   │   ├── useParlays.ts
│   │   │   ├── useOdds.ts
│   │   │   └── usePerformance.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .gitignore
├── Makefile
└── README.md
```

Backend deps: `fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, httpx, apscheduler, pandas, numpy, scikit-learn, pytest, pytest-asyncio`

Frontend deps: `react, react-dom, react-router-dom, @tanstack/react-query, recharts, tailwindcss, postcss, autoprefixer, axios, lucide-react, clsx`

### 1B: Docker Compose

```yaml
services:
  db:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: sharppicks
      POSTGRES_USER: sharppicks
      POSTGRES_PASSWORD: sharppicks_dev
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sharppicks"]
      interval: 5s
      retries: 5

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      db:
        condition: service_healthy
    env_file: ./backend/.env
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app

  worker:
    build: ./backend
    depends_on:
      db:
        condition: service_healthy
    env_file: ./backend/.env
    command: python -m app.worker
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    depends_on: [backend]
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  pgdata:
```

### 1C: Database Schema

Apply ALL indexes and constraints from Tweak 2. Apply `is_closing` flag from Tweak 9. Apply dual CLV fields from Tweak 5. Apply `prob_source` field from Tweak 3. Apply `data_quality` fields from Tweak 8.

Core tables:

- **sports** — id, key (e.g. "basketball_nba"), name, active (bool)
- **teams** — id, sport_id (FK), name, abbreviation
- **games** — id, external_id (unique), sport_id (FK), home_team_id, away_team_id, commence_time, home_score, away_score, status (upcoming/live/completed), created_at, updated_at
- **odds_snapshots** — id, game_id (FK), sport_key, bookmaker, market (h2h/spreads/totals), side (home/away/over/under), line (FLOAT nullable), odds (INT american), implied_prob (FLOAT), no_vig_prob (FLOAT), snapshot_time (TIMESTAMPTZ), is_closing (BOOL default false), snapshot_time_rounded (generated column truncated to minute). **Unique constraint on (game_id, bookmaker, market, side, snapshot_time_rounded)**. All compound indexes from Tweak 2.
- **game_stats** — id, game_id (FK), team_id (FK), stat_source, stats (JSONB), fetched_at
- **picks** — id, game_id (FK), sport_key, market, side, line, odds_american, best_book, fair_prob (NOT model_prob — Tweak 3), prob_source (VARCHAR default 'consensus'), implied_prob, ev_pct, composite_score, confidence_tier (high/medium/low), signals (JSONB), data_quality (JSONB — Tweak 8), suggested_kelly_fraction (FLOAT — Tweak 10), outcome (pending/win/loss/push), closing_consensus_prob, closing_book_prob, market_clv, book_clv, settled_at, created_at
- **parlays** — id, risk_level (conservative/moderate/aggressive), num_legs, combined_odds, combined_ev, correlation_score, suggested_kelly_fraction, outcome, profit_loss, created_at
- **parlay_legs** — id, parlay_id (FK), pick_id (FK), leg_order, result
- **bankroll_entries** — id, entry_type (deposit/withdrawal/bet/win), amount, balance_after, pick_id (FK nullable), parlay_id (FK nullable), notes, created_at
- **performance_snapshots** — id, snapshot_date, sport_key, market, confidence_tier, total_picks, wins, losses, pushes, hit_rate, roi_pct, avg_market_clv, avg_book_clv, units_won, max_drawdown

### 1D: Data Providers

**The Odds API client** (`data_providers/odds_api.py`):
- `get_sports()` → list active sports
- `get_odds(sport, regions="us", markets="h2h,spreads,totals", bookmakers=None)` → odds for upcoming games
- `get_scores(sport)` → scores for settling
- Track quota via `x-requests-remaining` response header, store in config/memory
- Implement delta detection: compare fetched odds to most recent DB snapshot, only insert if changed (Tweak 2)

**BallDontLie client** (`data_providers/balldontlie.py`):
- Games, player stats, team stats
- 5 req/min rate limit

**Rate limiter** (`data_providers/rate_limiter.py`): Token bucket pattern, per-provider, async-safe

### 1E: Task Scheduler (in worker container)

Use APScheduler with advisory locks (Tweak 6) on every task.

Adaptive polling logic (Tweak 1):
- `check_daily_schedule` — runs hourly, determines which sports have games today
- `fetch_odds_adaptive` — called by scheduler based on current window:
  - Off-hours: every 6 hours
  - Pre-game (3hr before first game): every 15 min, only today's active sports, top 8 books
  - Active games: every 10 min
- `fetch_scores` — every 30 min
- `fetch_stats` — daily 6am ET
- `generate_picks` — daily 9am ET + 2hr before first game of each sport
- `settle_picks` — every 30 min, includes is_closing flagging (Tweak 9) and dual CLV (Tweak 5)
- `update_polling_status` — continuous, updates `/api/v1/system/polling-status`

### 1F: Utility Functions (`utils/odds_math.py`)

- `american_to_decimal(american_odds: int) -> float`
- `decimal_to_american(decimal_odds: float) -> int`
- `american_to_implied_prob(american_odds: int) -> float`
- `implied_prob_to_american(prob: float) -> int`
- `remove_vig(probs: list[float]) -> list[float]` — normalize overround to sum to 1.0
- `calculate_ev(fair_prob: float, decimal_odds: float) -> float` — returns EV%
- `calculate_parlay_odds(legs: list[float]) -> float` — product of decimal odds
- `kelly_criterion(fair_prob: float, decimal_odds: float, fraction: float = 0.25) -> float` — Tweak 10

### Phase 1 Verification
```bash
docker compose up --build
# Wait for healthy, then:
curl http://localhost:8000/api/v1/sports
curl http://localhost:8000/api/v1/odds/live
curl http://localhost:8000/api/v1/system/polling-status
# Should return data from The Odds API stored in PostgreSQL
# Polling status should show current mode, quota remaining, next poll
```

---

## Phase 2: Analytics Engine & Pick Generation

### 2A: Data Quality Layer (Tweak 8 — do this FIRST in Phase 2)

`analytics/data_quality.py`:
- For each game, compute: `books_covered`, `snapshot_freshness_minutes`, `sharp_books_present` (check for pinnacle, betonline, bovada, circa), `line_dispersion` (std dev of no-vig probs), `market_completeness` (fraction of h2h+spreads+totals with data)
- Confidence caps based on quality (see Tweak 8 rules)
- Store quality metrics as JSONB on the pick record

### 2B: Consensus Odds (`analytics/consensus.py`)
- Average no-vig probabilities across all bookmakers = "fair probability" (NOT "model probability")
- Find best available line per game/market/side
- Detect outlier lines (any book > 2 std devs from consensus)
- Weight sharp books (Pinnacle, Circa) 2x in consensus calculation

### 2C: Line Movement Tracking (`analytics/line_movement.py`)
- Steam move detection: 3+ books shift same direction within 30 min (requires Tweak 1 adaptive polling)
- Reverse line movement: line moves opposite to expected public action
- Line freeze: heavy action on one side, no line movement
- Opening-to-current line change

### 2D: EV Calculator (`analytics/ev_calculator.py`)
- `fair_prob` = consensus no-vig probability (Tweak 3 naming)
- `ev_pct = (fair_prob * decimal(best_available_odds)) - 1`
- Rank all potential picks by EV%
- Include `prob_source = "consensus"` on every calculation

### 2E: Sharp Signals (`analytics/sharp_signals.py`)
Weighted composite score:

| Signal | Weight | Description |
|--------|--------|-------------|
| EV positive | 0.25 | EV% > 0 vs consensus |
| Steam move | 0.20 | Sharp money detected |
| Reverse line movement | 0.15 | RLM favoring this side |
| Best line available | 0.10 | Current line better than opening |
| Consensus deviation | 0.10 | Outlier book in our favor |
| Closing line trend | 0.10 | Historical CLV performance |
| Data quality | 0.10 | From data_quality.py (Tweak 8) |

### 2F: Confidence Tiers (`analytics/confidence.py`)
- **HIGH**: composite >= 0.70, EV% >= 5%, 3+ signals firing, data quality uncapped
- **MEDIUM**: composite >= 0.45, EV% >= 2%, 2+ signals
- **LOW**: passes minimum thresholds (composite >= 0.30, EV% >= 1%)
- **FILTERED OUT**: composite < 0.30 or EV% < 1%
- Apply data quality caps from Tweak 8 (e.g., < 4 books → max MEDIUM)

### 2G: Pick Generation (`services/pick_service.py`)
Pipeline: upcoming games → all markets → data quality check → consensus + EV → line movement + signals → confidence tier → filter → rank by EV → cap at ~10 picks/day
- Attach `suggested_kelly_fraction` to every pick (Tweak 10)
- Attach `data_quality` JSONB to every pick (Tweak 8)
- Attach `prob_source = "consensus"` to every pick (Tweak 3)

### Phase 2 Verification
```bash
curl http://localhost:8000/api/v1/picks/today
# Should return picks with:
# - confidence tiers (high/medium/low)
# - ev_pct
# - signal breakdown (JSONB)
# - fair_prob (not model_prob)
# - prob_source: "consensus"
# - data_quality metrics
# - suggested_kelly_fraction
# - best_book
```

---

## Phase 3: Parlay Builder

### 3A: Compatibility Matrix (Tweak 4 — do this FIRST)

`analytics/compatibility.py`:
- Hard blocks: same-game same-market, same-game same-side related markets (ML + spread same team)
- Correlation ceiling per risk level: Conservative 0.15, Moderate 0.40, Aggressive 0.70
- Return `(is_compatible: bool, reason: str)` for every pair

### 3B: Correlation Matrix (`analytics/correlation.py`)
- Domain-knowledge priors (see Tweak 4 for full list)
- After 500+ settled picks, blend in empirical correlations
- `P(A and B) = P(A)*P(B) + corr * sqrt(P(A)(1-P(A)) * P(B)(1-P(B)))`

### 3C: Parlay Construction (`services/parlay_service.py`)

| Level | Legs | Confidence | Target Odds | Strategy |
|-------|------|-----------|-------------|----------|
| Conservative | 2-3 | HIGH only | +150 to +300 | Uncorrelated (corr < 0.15), max EV |
| Moderate | 3-4 | HIGH + MED | +300 to +800 | Allow mild positive correlation |
| Aggressive | 4-6 | All tiers | +800 to +2500 | Seek positive correlation |

Greedy algorithm: start with highest-EV pick, iteratively add the pick that maximizes marginal combined EV weighted by correlation benefit. Check compatibility matrix before every addition.

Attach `suggested_kelly_fraction` to every parlay (Tweak 10).

### Phase 3 Verification
```bash
curl http://localhost:8000/api/v1/parlays/today
# Should return parlays at 3 risk levels with:
# - Legs with pick details
# - combined_odds, combined_ev
# - correlation_score
# - suggested_kelly_fraction
# - No hard-blocked combinations present
```

---

## Phase 4: React Dashboard

### Phase 4A (Build First):
- **Dashboard** (`/`) — Today's picks as cards (sport icon, teams, market, side, odds, best book, confidence badge, EV%, kelly units) + 3 parlay summary cards (conservative/moderate/aggressive)
- **Picks** (`/picks`) — Filterable table (sport, market, confidence, date range), expandable rows showing signal breakdown + data quality
- **Odds** (`/odds`) — Cross-bookmaker comparison table + line movement time-series chart (Recharts)

### Phase 4B (Build Second):
- **Parlays** (`/parlays`) — Pre-built parlays by risk level + interactive builder with live compatibility/correlation feedback

### Phase 4C (Build Last — Read-Only):
- **Performance** (`/performance`) — ROI over time, hit rate by sport/market, CLV distribution, calibration plot, confidence tier breakdown. Read-only, no forms.
- **Bankroll** (`/bankroll`) — Current balance, bet history, Kelly sizing info, balance chart. Read-only initially.

Tech: React Query (auto-refetch every 60s), Recharts, Tailwind dark theme, React Router v6, lucide-react icons.

### Phase 4 Verification
```bash
# Open http://localhost:5173
# Dashboard should show today's picks and parlays with live data
# Picks page should filter and expand with signal details
# Odds page should show cross-book comparison
```

---

## Phase 5: Performance Tracking & Refinement

### 5A: Settlement (`tasks/settle_picks.py`)
- Match completed game scores against pick side/line
- Determine closing snapshot (Tweak 5: last snapshot where `snapshot_time <= commence_time - 1 min`)
- Calculate dual CLV: market_clv and book_clv (Tweak 5)
- Grade picks: W/L/P
- Grade parlays: all legs must win

### 5B: Metrics (`services/performance_service.py`)
- Hit rate, ROI, average market CLV, average book CLV, units won, max drawdown
- Breakdowns by sport, market, confidence tier
- Daily snapshots in `performance_snapshots` table

### 5C: Model Refinement (after 200+ settled picks)
- Calibration analysis: fair_prob vs actual win rate
- Logistic regression on signal features → updated signal weights
- Tighten confidence thresholds based on observed hit rates
- Replace `prob_source: "consensus"` with `prob_source: "model_v1"` when real modeling is added
- Blend empirical correlations into prior correlation matrix

### Phase 5 Verification
```bash
# After games complete:
curl http://localhost:8000/api/v1/performance/summary
# Should show hit rate, ROI, market_clv, book_clv metrics
# Performance page should render charts
```

---

## Implementation Rules

1. **Build phase by phase. Verify each phase before moving to the next.**
2. **Every task uses advisory locks and upserts — no blind inserts.**
3. **Never call a probability "model_prob" until actual modeling exists. Use "fair_prob" with `prob_source: "consensus"`.**
4. **CLV data capture starts in Phase 1. Analysis starts in Phase 5.**
5. **Kelly sizing is present from Phase 2 onward on every pick and parlay.**
6. **Data quality gates confidence. Low quality data cannot produce high confidence picks.**
7. **Test odds_math.py, ev_calculator.py, and data_quality.py with unit tests.**
8. **Log everything: every odds snapshot, every pick generated, every settlement. Data is gold.**
