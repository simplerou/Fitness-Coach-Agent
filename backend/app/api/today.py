"""HTTP endpoints for today."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import select
from ..database import DailySignalRecord, WeeklyPlanRecord
from ..services.plan_service import week_start_for, serialize_today_schedule


def create_today_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.get("/api/today")
    def today(user_id: int = Depends(authenticated_user_id)) -> dict:
        selected_day = date.today()
        week_start = week_start_for(selected_day)
        with SessionLocal() as db:
            plan_record = db.scalar(select(WeeklyPlanRecord).where(
                WeeklyPlanRecord.user_id == user_id,
                WeeklyPlanRecord.week_start == week_start,
            ))
            today_schedule = serialize_today_schedule(
                plan_record.plan_data if plan_record is not None else None,
                selected_day,
            )
            if today_schedule["status"] == "rest":
                return {
                    "level": "rest_day",
                    "screening_date": None,
                    "message": "今天是当前周计划中的休息日，无需填写训练状态。",
                    "today_schedule": today_schedule,
                    "plan_items": [],
                    "reasons": ["计划休息日无需提交训练状态"],
                }

            signal_record = db.scalar(select(DailySignalRecord).where(
                DailySignalRecord.user_id == user_id,
                DailySignalRecord.signal_date == selected_day,
            ))
            signal = (
                {
                    "readiness": signal_record.readiness,
                    "sleep_hours": signal_record.sleep_hours,
                    "resting_hr": signal_record.resting_hr,
                }
                if signal_record else None
            )

        if signal is None:
            return {
                "level": "insufficient_data",
                "screening_date": None,
                "message": "还没有记录今天的主观状态，暂时无法判断是否需要调整。",
                "today_schedule": today_schedule,
                "plan_items": [],
                "reasons": ["今日状态数据未提供；缺失不代表状态正常"],
            }
        if signal["readiness"] == "poor":
            return {
                "level": "downgrade",
                "screening_date": None,
                "message": "你报告今天状态较差。考虑降低训练强度或休息；如有疼痛或明显不适，请停止训练并寻求专业帮助。",
                "today_schedule": today_schedule,
                "plan_items": [],
                "reasons": ["依据：用户报告今日状态较差"],
            }

        today_session = today_schedule["session"]
        return {
            "level": "normal",
            "screening_date": None,
            "message": f"你报告今天状态尚可。{today_schedule['message']}",
            "today_schedule": today_schedule,
            "plan_items": [today_session] if today_schedule["status"] == "training" else [],
            "reasons": [f"依据：用户报告今日状态为 {'良好' if signal['readiness'] == 'good' else '一般'}"],
        }

    return router
