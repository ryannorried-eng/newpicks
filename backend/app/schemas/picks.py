from datetime import date, datetime

from pydantic import BaseModel


class PickResponse(BaseModel):
    id: int
    game_id: int
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime
    pick_day: date | None = None
    market: str
    side: str
    line: float | None
    odds_american: int
    best_book: str

    issued_at: datetime | None = None
    snapshot_time_open: datetime | None = None
    model_prob: float | None = None
    implied_prob_open: float | None = None
    ev_pct: float | None = None
    edge: float | None = None
    consensus_prob: float | None = None
    book_count: int | None = None

    closing_odds_american: int | None = None
    closing_line: float | None = None
    closing_snapshot_time: datetime | None = None
    clv_prob: float | None = None
    clv_price: float | None = None

    status: str | None = None
    result: str | None = None
    settled_at: datetime | None = None
    pnl_units: float | None = None

    fair_prob: float | None = None
    prob_source: str | None = None
    implied_prob: float | None = None
    composite_score: float | None = None
    confidence_tier: str | None = None
    signals: dict | None = None
    data_quality: dict | None = None
    suggested_kelly_fraction: float | None = None
    outcome: str | None
    market_clv: float | None
    book_clv: float | None
    created_at: datetime


class PicksHistoryParams(BaseModel):
    sport: str | None = None
    market: str | None = None
    confidence: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = 50
