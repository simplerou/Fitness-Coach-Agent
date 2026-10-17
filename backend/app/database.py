# 数据库模块：管理 PostgreSQL 连接、ORM 表结构、租户迁移和用户初始化。
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text,
    create_engine, func, select, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("未设置 DATABASE_URL。请复制 .env.example 为 .env，并填写本机 PostgreSQL 连接信息。")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


DEFAULT_TRAINING_WEEKDAYS_BY_COUNT = {
    1: [1], 2: [1, 4], 3: [1, 3, 5], 4: [1, 2, 4, 6],
    5: [1, 2, 3, 5, 6], 6: [1, 2, 3, 4, 5, 6],
}


class AccountUserRecord(Base):
    """账号表；只保存密码散列，不保存原始密码。"""

    __tablename__ = "account_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(48), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DailySignalRecord(Base):
    __tablename__ = "daily_signals"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    readiness: Mapped[str] = mapped_column(String(16), nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)


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


class LocalProfileRecord(Base):
    __tablename__ = "local_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    registered_on: Mapped[date] = mapped_column(Date, nullable=False)


class BodyProfileRecord(Base):
    """一个账号一份当前身体档案；体重历史另存，便于回看变化。"""

    __tablename__ = "body_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    age_band: Mapped[str] = mapped_column(String(16), nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class BodyWeightHistoryRecord(Base):
    __tablename__ = "body_weight_history"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    recorded_on: Mapped[date] = mapped_column(Date, primary_key=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class TrainingSchedulePreferencesRecord(Base):
    __tablename__ = "training_schedule_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    weekdays: Mapped[list[int]] = mapped_column(JSON, nullable=False)


class LocalSafetyStateRecord(Base):
    __tablename__ = "local_safety_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), nullable=False, unique=True)
    hold_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_requires_professional_confirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


TENANT_TABLES = (
    "daily_signals", "training_logs", "local_profiles", "body_profiles",
    "body_weight_history", "weekly_plans", "training_preferences",
    "training_schedule_preferences", "local_safety_state",
)


def initialize_database() -> None:
    """建表并为旧版单用户表预留账号归属列；实际归属在首个注册时迁移。"""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        for table_name in TENANT_TABLES:
            connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS user_id INTEGER'))
        connection.execute(text('ALTER TABLE local_safety_state ADD COLUMN IF NOT EXISTS hold_date DATE'))
        connection.execute(text('ALTER TABLE body_profiles ADD COLUMN IF NOT EXISTS target_weight_kg FLOAT'))
        connection.execute(text('ALTER TABLE training_logs ADD COLUMN IF NOT EXISTS planned_session_title VARCHAR(120)'))
        connection.execute(text(
            'UPDATE local_safety_state SET hold_date = CURRENT_DATE '
            'WHERE hold_active = TRUE AND hold_date IS NULL'
        ))


def claim_legacy_data_for_first_user(db, user_id: int) -> None:
    """首个注册账号继承旧版单用户数据，并将日期键改为账号复合键。"""
    for table_name in TENANT_TABLES:
        db.execute(text(f'UPDATE "{table_name}" SET user_id = :user_id WHERE user_id IS NULL'), {"user_id": user_id})

    date_key_tables = {
        "daily_signals": "signal_date",
        "body_weight_history": "recorded_on",
        "weekly_plans": "week_start",
    }
    for table_name, date_column in date_key_tables.items():
        db.execute(text(f'ALTER TABLE "{table_name}" DROP CONSTRAINT IF EXISTS "{table_name}_pkey"'))
        db.execute(text(
            f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{table_name}_pkey" PRIMARY KEY (user_id, "{date_column}")'
        ))

    for table_name in TENANT_TABLES:
        db.execute(text(f'ALTER TABLE "{table_name}" ALTER COLUMN user_id SET NOT NULL'))
        constraint_name = f'{table_name}_user_id_fkey'
        exists = db.scalar(text('SELECT 1 FROM pg_constraint WHERE conname = :name'), {"name": constraint_name})
        if not exists:
            db.execute(text(
                f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" '
                'FOREIGN KEY (user_id) REFERENCES account_users(id) ON DELETE CASCADE'
            ))

    for table_name in (
        "local_profiles", "body_profiles", "training_preferences",
        "training_schedule_preferences", "local_safety_state",
    ):
        db.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "uq_{table_name}_user_id" ON "{table_name}" (user_id)'))
    db.execute(text('CREATE INDEX IF NOT EXISTS "ix_training_logs_user_date" ON training_logs (user_id, training_date)'))
    # 老版单例曾显式写入 id=1，推进自增序列，避免第二个账号的默认行撞主键。
    for table_name in ("local_profiles", "body_profiles", "training_preferences", "training_schedule_preferences", "local_safety_state"):
        db.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 1), 1), "
            f"EXISTS(SELECT 1 FROM {table_name}))"
        ))


def initialize_user_defaults(db, user_id: int, registered_on: date) -> None:
    """为新账号创建独立起始日期、安全状态和训练偏好。"""
    local_profile = db.scalar(select(LocalProfileRecord).where(LocalProfileRecord.user_id == user_id))
    if local_profile is None:
        db.add(LocalProfileRecord(user_id=user_id, registered_on=registered_on))

    safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
    if safety_state is None:
        db.add(LocalSafetyStateRecord(user_id=user_id, hold_active=False, hold_requires_professional_confirmation=False, hold_date=None))

    preferences = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
    if preferences is None:
        preferences = TrainingPreferencesRecord(
            user_id=user_id, goal="fitness", days_per_week=3,
            experience_level="beginner", equipment=["bodyweight_only"], session_minutes=30,
        )
        db.add(preferences)
        db.flush()

    schedule = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
    if schedule is None:
        days = preferences.days_per_week
        db.add(TrainingSchedulePreferencesRecord(
            user_id=user_id, weekdays=DEFAULT_TRAINING_WEEKDAYS_BY_COUNT.get(days, [1, 3, 5]),
        ))
