from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Pick(Base):
    __tablename__ = "picks"
    __table_args__ = (
        UniqueConstraint("game_id", "market", "side", "pick_date", name="uq_pick_daily_side"),
        UniqueConstraint("game_id", "market", "side", "pick_day", name="uq_pick_game_market_side_day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    sport_key: Mapped[str] = mapped_column(String(64), index=True)
    pick_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    pick_day: Mapped[date] = mapped_column(Date, index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(32), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    odds_american: Mapped[int] = mapped_column(Integer)
    best_book: Mapped[str] = mapped_column(String(64))

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot_time_open: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    model_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    implied_prob_open: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge: Mapped[float | None] = mapped_column(Float, nullable=True)
    consensus_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    book_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    closing_odds_american: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_snapshot_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clv_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    result: Mapped[str | None] = mapped_column(String(8), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pnl_units: Mapped[float | None] = mapped_column(Float, nullable=True)

    # legacy/compat fields still used elsewhere
    fair_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    prob_source: Mapped[str] = mapped_column(String(32), default="consensus")
    implied_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_tier: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    signals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_quality: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggested_kelly_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(16), nullable=True)
    profit_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    book_clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
