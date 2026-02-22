from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Pick(Base):
    __tablename__ = "picks"
    __table_args__ = (
        UniqueConstraint("game_id", "market", "side", "pick_date", name="uq_pick_daily_side"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    sport_key: Mapped[str] = mapped_column(String(64), index=True)
    pick_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(32), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    odds_american: Mapped[int] = mapped_column(Integer)
    best_book: Mapped[str] = mapped_column(String(64))
    fair_prob: Mapped[float] = mapped_column(Float)
    prob_source: Mapped[str] = mapped_column(String(32), default="consensus")
    implied_prob: Mapped[float] = mapped_column(Float)
    ev_pct: Mapped[float] = mapped_column(Float)
    composite_score: Mapped[float] = mapped_column(Float)
    confidence_tier: Mapped[str] = mapped_column(String(16), index=True)
    signals: Mapped[dict] = mapped_column(JSON)
    data_quality: Mapped[dict] = mapped_column(JSON)
    suggested_kelly_fraction: Mapped[float] = mapped_column(Float)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    market_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    book_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
