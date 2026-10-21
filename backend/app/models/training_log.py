"""training_log ?????"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class TrainingLogRecord(Base):
    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    training_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completion: Mapped[str] = mapped_column(String(16), nullable=False)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_session_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
