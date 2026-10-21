"""training_plan ?????"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WeeklyPlanRecord(Base):
    __tablename__ = "weekly_plans"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, primary_key=True)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TrainingPreferencesRecord(Base):
    __tablename__ = "training_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    goal: Mapped[str] = mapped_column(String(16), nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    experience_level: Mapped[str] = mapped_column(String(24), nullable=False)
    equipment: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    session_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred_exercise_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TrainingSchedulePreferencesRecord(Base):
    __tablename__ = "training_schedule_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    weekdays: Mapped[list[int]] = mapped_column(JSON, nullable=False)
