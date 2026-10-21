"""HTTP endpoints for safety."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from ..database import LocalSafetyStateRecord
from ..schemas.safety import SafetyCheck
from ..services.safety_service import SCREENING_DATES, SYMPTOM_LABELS


def create_safety_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.post("/api/safety-check")
    def safety_check(payload: SafetyCheck, user_id: int = Depends(authenticated_user_id)) -> dict:
        today = date.today()
        SCREENING_DATES.pop(user_id, None)
        with SessionLocal() as db:
            safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
            if safety_state is None:
                raise HTTPException(status_code=503, detail="本地安全状态缺失，请重启服务初始化数据库后重试。")
            if safety_state.hold_active and safety_state.hold_date == today:
                return {
                    "status": "stop",
                    "screening_date": today.isoformat(),
                    "message": "今天的训练建议已暂停，请休息。若出现紧急或严重症状，请及时联系当地急救或医疗服务。",
                    "symptoms": [],
                }
            if not payload.completed:
                return {"status": "ask", "message": "请确认今天的身体感受。", "symptoms": []}
            if payload.no_symptoms and payload.symptoms:
                raise HTTPException(status_code=422, detail="不能同时选择“没有不适”和“有不适或无法判断”。")
            if payload.symptoms:
                safety_state.hold_active = True
                safety_state.hold_date = today
                safety_state.hold_requires_professional_confirmation = False
                db.commit()
                labels = [SYMPTOM_LABELS[item] for item in payload.symptoms]
                return {
                    "status": "stop",
                    "screening_date": today.isoformat(),
                    "message": "今天先暂停训练建议并休息。若症状紧急、严重、持续或加重，请及时联系医疗服务。",
                    "symptoms": labels,
                }
            if not payload.no_symptoms:
                return {"status": "ask", "message": "请确认今天是否有明显不适。", "symptoms": []}
            safety_state.hold_active = False
            safety_state.hold_date = None
            safety_state.hold_requires_professional_confirmation = False
            db.commit()
        SCREENING_DATES[user_id] = today
        return {
            "status": "clear",
            "screening_date": today.isoformat(),
            "message": "今日身体状态已确认。",
            "symptoms": [],
        }

    return router
