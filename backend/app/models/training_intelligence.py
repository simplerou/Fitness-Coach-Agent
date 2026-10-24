"""动作库、动作级训练记录、恢复打卡与训练建议数据模型。"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ExerciseLibraryRecord(Base):
    __tablename__ = "exercise_library"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    target_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    equipment: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    cues: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    common_errors: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    regressions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    progressions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    alternatives: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    demo_images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    demo_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_credit: Mapped[str | None] = mapped_column(String(160), nullable=True)
    media_license: Mapped[str | None] = mapped_column(String(80), nullable=True)
    media_source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_seed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ExerciseKnowledgeDocumentRecord(Base):
    """经审核的外部训练资料摘要与动作库检索文档；不按用户隔离，作为公共知识库。"""
    __tablename__ = "exercise_knowledge_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercise_library.id", ondelete="SET NULL"), nullable=True, index=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_uploads.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(String(180), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_published_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_retrieved_at: Mapped[date] = mapped_column(Date, nullable=False)
    content_rights: Mapped[str] = mapped_column(String(80), nullable=False, default="paraphrased_summary")
    target_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    equipment: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved", index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TrainingExerciseEntryRecord(Base):
    __tablename__ = "training_exercise_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("training_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise_library.id"), nullable=False, index=True)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps_min: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps_max: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rpe: Mapped[int] = mapped_column(Integer, nullable=False)
    completion: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RecoveryCheckinRecord(Base):
    __tablename__ = "recovery_checkins"
    __table_args__ = (UniqueConstraint("log_id", name="uq_recovery_checkins_log_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("training_logs.id", ondelete="CASCADE"), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    soreness: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_hours: Mapped[float] = mapped_column(Float, nullable=False)
    sleep_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    is_sick: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    warning_symptom: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class ExerciseAdviceRecord(Base):
    __tablename__ = "exercise_advice"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_id: Mapped[int] = mapped_column(ForeignKey("training_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercise_library.id"), nullable=False, index=True)
    advice_type: Mapped[str] = mapped_column(String(16), nullable=False)
    prescription: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PlanAdjustmentRecord(Base):
    __tablename__ = "plan_adjustments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_week_start: Mapped[date] = mapped_column(Date, nullable=False)
    target_week_start: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

