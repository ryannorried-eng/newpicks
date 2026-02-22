from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.picks import PickResponse


class ParlayLegResponse(BaseModel):
    id: int
    pick_id: int
    leg_order: int
    result: str | None
    pick: PickResponse


class ParlayResponse(BaseModel):
    id: int
    risk_level: str
    num_legs: int
    combined_odds_american: int
    combined_odds_decimal: float
    combined_ev_pct: float
    combined_fair_prob: float
    correlation_score: float
    suggested_kelly_fraction: float
    outcome: str | None
    profit_loss: float | None
    created_at: datetime
    legs: list[ParlayLegResponse]


class ParlayBuildRequest(BaseModel):
    pick_ids: list[int]


class ParlayBuildResponse(BaseModel):
    is_valid: bool
    reason: str
    combined_odds_american: int | None = None
    combined_odds_decimal: float | None = None
    combined_ev_pct: float | None = None
    combined_fair_prob: float | None = None
    correlation_score: float | None = None
    compatibility_warnings: list[str] = []
    suggested_kelly_fraction: float | None = None
