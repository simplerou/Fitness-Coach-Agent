"""减脂塑形智能联动层的数据快照与用户决策。"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ShapingPreferenceRecord(Base):
    __tablename__ = "shaping_intelligence_preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    goal: Mapped[str] = mapped_column(String(24), nullable=False, default="whole_body")
    focus_groups: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    excluded_groups: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MuscleGroupStatRecord(Base):
    __tablename__ = "muscle_group_stats"
    __table_args__ = (UniqueConstraint("user_id", "period_start", "period_end", "muscle_group", name="uq_muscle_stat_period"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    muscle_group: Mapped[str] = mapped_column(String(16), nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    total_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeakPartAdviceRecord(Base):
    __tablename__ = "weak_part_advice"
    __table_args__ = (UniqueConstraint("user_id", "period_end", "muscle_group", name="uq_weak_part_period"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    muscle_group: Mapped[str] = mapped_column(String(16), nullable=False)
    advice_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QaLogRecord(Base):
    __tablename__ = "qa_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(24), nullable=False)
    exercise_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    used_llm: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DietDayAdjustmentRecord(Base):
    __tablename__ = "diet_day_adjustment"
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    adjustment_date: Mapped[date] = mapped_column(Date, primary_key=True)
    day_type: Mapped[str] = mapped_column(String(20), nullable=False)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False)
    suggestion: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReportSnapshotRecord(Base):
    __tablename__ = "report_snapshot"
    __table_args__ = (UniqueConstraint("user_id", "period_type", "period_start", name="uq_shape_report_period"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(String(12), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
