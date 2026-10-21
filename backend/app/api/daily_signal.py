"""HTTP endpoints for daily signal."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select
from ..database import DailySignalRecord
from ..schemas.daily_signal import DailySignal


def create_daily_signal_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.post("/api/daily-signal")
    def save_daily_signal(payload: DailySignal, user_id: int = Depends(authenticated_user_id)) -> dict:
        today = date.today()
        with SessionLocal() as db:
            record = db.scalar(select(DailySignalRecord).where(DailySignalRecord.user_id == user_id, DailySignalRecord.signal_date == today))
            if record is None:
                record = DailySignalRecord(user_id=user_id, signal_date=today, **payload.model_dump())
                db.add(record)
            else:
                record.readiness = payload.readiness
                record.sleep_hours = payload.sleep_hours
                record.resting_hr = payload.resting_hr
            db.commit()
        return {
            "accepted": True,
            "source": "manual",
            "recorded_at": today.isoformat(),
            "message": "状态已保存到本机 PostgreSQL 数据库。",
        }

    return router
