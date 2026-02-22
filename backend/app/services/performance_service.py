from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pick import Pick


@dataclass
class PerformanceSummary:
    total_picks: int
    settled_picks: int
    pending_picks: int
    wins: int
    losses: int
    pushes: int
    win_rate: float
    roi_pct: float
    total_profit_units: float
    avg_ev_pct: float
    avg_market_clv: float
    avg_book_clv: float
    avg_odds_american: float
    high_confidence: dict
    medium_confidence: dict
    low_confidence: dict
    by_sport: dict
    by_market: dict


def _bucket(rows: list[Pick], attr: str) -> dict:
    out: dict = {}
    for pick in rows:
        key = getattr(pick, attr)
        wins = 1 if pick.outcome == "win" else 0
        losses = 1 if pick.outcome == "loss" else 0
        out.setdefault(key, {"picks": 0, "wins": 0, "losses": 0, "profit": 0.0, "clv": []})
        b = out[key]
        b["picks"] += 1
        b["wins"] += wins
        b["losses"] += losses
        b["profit"] += pick.profit_loss or 0.0
        if pick.market_clv is not None:
            b["clv"].append(pick.market_clv)

    for key, b in out.items():
        wagered = sum((p.suggested_kelly_fraction or 0.0) for p in rows if getattr(p, attr) == key)
        b["roi"] = (b["profit"] / wagered * 100.0) if wagered > 0 else 0.0
        b["avg_clv"] = sum(b["clv"]) / len(b["clv"]) if b["clv"] else 0.0
        del b["profit"]
        del b["clv"]
    return out


async def get_performance_summary(
    session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    sport_key: str | None = None,
) -> PerformanceSummary:
    stmt = select(Pick)
    if start_date:
        stmt = stmt.where(Pick.pick_date >= start_date)
    if end_date:
        stmt = stmt.where(Pick.pick_date <= end_date)
    if sport_key:
        stmt = stmt.where(Pick.sport_key == sport_key)

    rows = (await session.scalars(stmt)).all()
    settled = [p for p in rows if p.outcome in {"win", "loss", "push"}]
    wins = sum(1 for p in settled if p.outcome == "win")
    losses = sum(1 for p in settled if p.outcome == "loss")
    pushes = sum(1 for p in settled if p.outcome == "push")

    total_profit = sum(p.profit_loss or 0.0 for p in settled)
    total_wagered = sum(p.suggested_kelly_fraction or 0.0 for p in settled)
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0

    tier_map = _bucket(settled, "confidence_tier")
    return PerformanceSummary(
        total_picks=len(rows),
        settled_picks=len(settled),
        pending_picks=len(rows) - len(settled),
        wins=wins,
        losses=losses,
        pushes=pushes,
        win_rate=win_rate,
        roi_pct=(total_profit / total_wagered * 100.0) if total_wagered > 0 else 0.0,
        total_profit_units=total_profit,
        avg_ev_pct=(sum(p.ev_pct for p in rows) / len(rows)) if rows else 0.0,
        avg_market_clv=(sum(p.market_clv for p in settled if p.market_clv is not None) / len([p for p in settled if p.market_clv is not None])) if any(p.market_clv is not None for p in settled) else 0.0,
        avg_book_clv=(sum(p.book_clv for p in settled if p.book_clv is not None) / len([p for p in settled if p.book_clv is not None])) if any(p.book_clv is not None for p in settled) else 0.0,
        avg_odds_american=(sum(p.odds_american for p in rows) / len(rows)) if rows else 0.0,
        high_confidence=tier_map.get("high", {"picks": 0, "wins": 0, "losses": 0, "roi": 0.0, "avg_clv": 0.0}),
        medium_confidence=tier_map.get("medium", {"picks": 0, "wins": 0, "losses": 0, "roi": 0.0, "avg_clv": 0.0}),
        low_confidence=tier_map.get("low", {"picks": 0, "wins": 0, "losses": 0, "roi": 0.0, "avg_clv": 0.0}),
        by_sport=_bucket(settled, "sport_key"),
        by_market=_bucket(settled, "market"),
    )


async def get_daily_performance(session: AsyncSession, days: int = 30) -> list[dict]:
    start = date.today() - timedelta(days=days - 1)
    rows = (
        await session.execute(
            select(
                func.date(Pick.created_at).label("d"),
                func.count(Pick.id).label("picks"),
                func.sum(func.case((Pick.outcome == "win", 1), else_=0)).label("wins"),
                func.sum(func.case((Pick.outcome == "loss", 1), else_=0)).label("losses"),
                func.sum(func.coalesce(Pick.profit_loss, 0.0)).label("profit"),
                func.sum(func.coalesce(Pick.suggested_kelly_fraction, 0.0)).label("wagered"),
                func.avg(Pick.market_clv).label("avg_clv"),
            )
            .where(and_(func.date(Pick.created_at) >= start, Pick.outcome.in_(["win", "loss", "push"])))
            .group_by("d")
            .order_by("d")
        )
    ).all()

    cumulative = 0.0
    out: list[dict] = []
    for r in rows:
        cumulative += float(r.profit or 0.0)
        out.append(
            {
                "date": str(r.d),
                "picks": int(r.picks or 0),
                "wins": int(r.wins or 0),
                "losses": int(r.losses or 0),
                "roi": (float(r.profit or 0.0) / float(r.wagered or 0.0) * 100.0) if float(r.wagered or 0.0) > 0 else 0.0,
                "cumulative_profit": cumulative,
                "avg_clv": float(r.avg_clv or 0.0),
            }
        )
    return out


async def get_roi_over_time(session: AsyncSession) -> list[dict]:
    daily = await get_daily_performance(session, days=3650)
    cumulative_picks = 0
    out: list[dict] = []
    for item in daily:
        cumulative_picks += item["picks"]
        total_wagered_stmt = select(func.sum(Pick.suggested_kelly_fraction)).where(
            func.date(Pick.created_at) <= item["date"], Pick.outcome.in_(["win", "loss", "push"])
        )
        total_wagered = float(await session.scalar(total_wagered_stmt) or 0.0)
        out.append(
            {
                "date": item["date"],
                "cumulative_picks": cumulative_picks,
                "cumulative_profit": item["cumulative_profit"],
                "cumulative_roi_pct": (item["cumulative_profit"] / total_wagered * 100.0) if total_wagered > 0 else 0.0,
            }
        )
    return out


def summary_to_dict(summary: PerformanceSummary) -> dict:
    return asdict(summary)
