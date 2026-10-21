"""HTTP endpoints for log."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from ..database import TrainingLogRecord, WeeklyPlanRecord
from ..schemas.training_log import TrainingLog
from ..services.plan_service import week_start_for, serialize_today_schedule
from ..services.profile_service import get_registration_date


def create_log_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.post("/api/log")
    def create_log(payload: TrainingLog, user_id: int = Depends(authenticated_user_id)) -> dict:
        if payload.completion == "skipped" and payload.skip_reason is None:
            raise HTTPException(status_code=422, detail="未完成训练时，请选择未完成原因。")
        with SessionLocal() as db:
            registration_date = get_registration_date(db, user_id)
            if payload.training_date < registration_date:
                raise HTTPException(status_code=422, detail="训练日期早于本地档案起始日期，不能保存该记录。")
            plan_record = db.scalar(select(WeeklyPlanRecord).where(
                WeeklyPlanRecord.user_id == user_id,
                WeeklyPlanRecord.week_start == week_start_for(payload.training_date),
            ))
            schedule = serialize_today_schedule(
                plan_record.plan_data if plan_record is not None else None,
                payload.training_date,
            )
            planned_session = schedule.get("session") if schedule.get("status") == "training" else None
            planned_title = planned_session.get("title") if isinstance(planned_session, dict) else None
            record = TrainingLogRecord(
                user_id=user_id,
                **payload.model_dump(),
                planned_session_title=planned_title,
            )
            db.add(record)
            db.commit()
        entry = payload.model_dump(mode="json")
        entry["planned_session_title"] = planned_title
        plan_message = f"已关联计划训练：{planned_title}。" if planned_title else ""
        return {"ok": True, "log": entry, "message": "训练记录已保存到本机 PostgreSQL 数据库。" + plan_message}

    @router.get("/api/plan/session")
    def plan_session_for_date(
        training_date: date | None = Query(default=None),
        user_id: int = Depends(authenticated_user_id),
    ) -> dict:
        selected_day = training_date or date.today()
        with SessionLocal() as db:
            registration_date = get_registration_date(db, user_id)
            if selected_day < registration_date:
                return {"training_date": selected_day.isoformat(), "status": "before_registration", "session": None}
            record = db.scalar(select(WeeklyPlanRecord).where(
                WeeklyPlanRecord.user_id == user_id,
                WeeklyPlanRecord.week_start == week_start_for(selected_day),
            ))
            schedule = serialize_today_schedule(record.plan_data if record is not None else None, selected_day)
        return {"training_date": selected_day.isoformat(), **schedule}

    @router.get("/api/logs")
    def list_logs(
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = Query(default=20, ge=1, le=500),
        user_id: int = Depends(authenticated_user_id),
    ) -> dict:
        if from_date and to_date and from_date > to_date:
            raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期。")
        with SessionLocal() as db:
            registration_date = get_registration_date(db, user_id)
            query = select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id, TrainingLogRecord.training_date >= registration_date)
            if from_date:
                query = query.where(TrainingLogRecord.training_date >= from_date)
            if to_date:
                query = query.where(TrainingLogRecord.training_date <= to_date)
            records = db.scalars(
                query.order_by(TrainingLogRecord.training_date.desc(), TrainingLogRecord.id.desc())
                .limit(limit)
            ).all()
            items = [
                {
                    "training_date": record.training_date.isoformat(),
                    "completion": record.completion,
                    "rpe": record.rpe,
                    "skip_reason": record.skip_reason,
                    "note": record.note,
                    "planned_session_title": record.planned_session_title,
                }
                for record in records
            ]
        return {"items": items}

    return router
