"""safety_hold ?????"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LocalSafetyStateRecord(Base):
    __tablename__ = "local_safety_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    hold_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_requires_professional_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
