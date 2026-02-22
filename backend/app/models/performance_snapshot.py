from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PerformanceSnapshot(Base):
    __tablename__ = "performance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    total_picks: Mapped[int] = mapped_column(Integer, default=0)
    settled_picks: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    pushes: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    roi_pct: Mapped[float] = mapped_column(Float, default=0.0)
    total_profit_units: Mapped[float] = mapped_column(Float, default=0.0)
    avg_ev_pct: Mapped[float] = mapped_column(Float, default=0.0)
    avg_market_clv: Mapped[float] = mapped_column(Float, default=0.0)
    avg_book_clv: Mapped[float] = mapped_column(Float, default=0.0)
    by_sport: Mapped[dict] = mapped_column(JSON, default=dict)
    by_market: Mapped[dict] = mapped_column(JSON, default=dict)
    by_tier: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
