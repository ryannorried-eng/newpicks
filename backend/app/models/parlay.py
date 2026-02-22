from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Parlay(Base):
    __tablename__ = "parlays"
    __table_args__ = (
        UniqueConstraint("risk_level", "pick_date", "combined_odds_american", name="uq_parlay_daily_exact"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    num_legs: Mapped[int] = mapped_column(Integer)
    combined_odds_american: Mapped[int] = mapped_column(Integer)
    combined_odds_decimal: Mapped[float] = mapped_column(Float)
    combined_ev_pct: Mapped[float] = mapped_column(Float)
    combined_fair_prob: Mapped[float] = mapped_column(Float)
    correlation_score: Mapped[float] = mapped_column(Float)
    suggested_kelly_fraction: Mapped[float] = mapped_column(Float)
    outcome: Mapped[str] = mapped_column(String(16), default="pending")
    profit_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    pick_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    legs: Mapped[list["ParlayLeg"]] = relationship("ParlayLeg", back_populates="parlay", order_by="ParlayLeg.leg_order")


class ParlayLeg(Base):
    __tablename__ = "parlay_legs"

    id: Mapped[int] = mapped_column(primary_key=True)
    parlay_id: Mapped[int] = mapped_column(ForeignKey("parlays.id"), index=True)
    pick_id: Mapped[int] = mapped_column(ForeignKey("picks.id"), index=True)
    leg_order: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(16), default="pending")

    parlay: Mapped[Parlay] = relationship("Parlay", back_populates="legs")
    pick = relationship("Pick")
