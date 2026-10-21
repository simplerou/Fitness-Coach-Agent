"""diet ?????"""
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class DietMealRecord(Base):
    __tablename__ = "diet_meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    note: Mapped[str | None] = mapped_column(String(240), nullable=True)
    portion: Mapped[str | None] = mapped_column(String(120), nullable=True)
    eaten_at: Mapped[str | None] = mapped_column(String(5), nullable=True)
    calories_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    nutrition_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DietProfileRecord(Base):
    __tablename__ = "diet_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    # Legacy demographic and measurement columns stay mapped for old databases; current reads use body_profiles.
    age_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    biological_sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_bmr: Mapped[float | None] = mapped_column(Float, nullable=True)
    measured_tdee: Mapped[float | None] = mapped_column(Float, nullable=True)
    goal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    training_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    training_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    training_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    dietary_preference: Mapped[str | None] = mapped_column(String(48), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergies_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avoid_foods: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    injuries: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cooking_access: Mapped[str | None] = mapped_column(String(24), nullable=True)
    eating_out_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_note: Mapped[str | None] = mapped_column(String(160), nullable=True)
    water_target_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DietDayReviewRecord(Base):
    __tablename__ = "diet_day_reviews"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    log_date: Mapped[date] = mapped_column(Date, primary_key=True)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DietPlanSnapshotRecord(Base):
    __tablename__ = "diet_plan_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plan_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DailyWaterRecord(Base):
    __tablename__ = "daily_water_intakes"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    log_date: Mapped[date] = mapped_column(Date, primary_key=True)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
