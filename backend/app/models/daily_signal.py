"""daily_signal ?????"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class DailySignalRecord(Base):
    __tablename__ = "daily_signals"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    readiness: Mapped[str] = mapped_column(String(16), nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
