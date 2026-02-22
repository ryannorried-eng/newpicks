from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BankrollEntry(Base):
    __tablename__ = "bankroll_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    pick_id: Mapped[int | None] = mapped_column(ForeignKey("picks.id"), nullable=True, index=True)
    entry_type: Mapped[str] = mapped_column(String(32), index=True)
    amount: Mapped[float] = mapped_column(Float)
    balance_after: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
