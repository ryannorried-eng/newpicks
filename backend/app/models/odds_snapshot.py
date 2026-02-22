from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "bookmaker",
            "market",
            "side",
            "snapshot_time_rounded",
            name="uq_odds_snapshot_minute",
        ),
        Index("ix_odds_sport_commence", "sport_key", "commence_time"),
        Index("ix_odds_game_market_time", "game_id", "market", "snapshot_time"),
        Index("ix_odds_book_market_time", "bookmaker", "market", "snapshot_time"),
        Index(
            "ix_odds_game_book_market_side",
            "game_id",
            "bookmaker",
            "market",
            "side",
            "snapshot_time",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    sport_key: Mapped[str] = mapped_column(String(64), index=True)
    bookmaker: Mapped[str] = mapped_column(String(64), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(32), index=True)
    line: Mapped[float | None] = mapped_column(Float)
    odds: Mapped[int] = mapped_column(Integer)
    implied_prob: Mapped[float] = mapped_column(Float)
    no_vig_prob: Mapped[float] = mapped_column(Float)
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    snapshot_time_rounded: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_closing: Mapped[bool] = mapped_column(default=False)
