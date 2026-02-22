from datetime import datetime

from pydantic import BaseModel


class PickResponse(BaseModel):
    id: int
    game_id: int
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime
    market: str
    side: str
    line: float | None
    odds_american: int
    best_book: str
    fair_prob: float
    prob_source: str
    implied_prob: float
    ev_pct: float
    composite_score: float
    confidence_tier: str
    signals: dict
    data_quality: dict
    suggested_kelly_fraction: float
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
