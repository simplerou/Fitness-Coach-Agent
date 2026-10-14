from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Date, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "未设置 DATABASE_URL。请复制 .env.example 为 .env，并填写本机 PostgreSQL 连接信息。"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DailySignalRecord(Base):
    __tablename__ = "daily_signals"

    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    readiness: Mapped[str] = mapped_column(String(16), nullable=False)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TrainingLogRecord(Base):
    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    training_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    completion: Mapped[str] = mapped_column(String(16), nullable=False)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
