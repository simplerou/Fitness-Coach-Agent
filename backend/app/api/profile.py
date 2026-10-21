"""HTTP endpoints for profile."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from ..database import BodyProfileRecord, BodyWeightHistoryRecord, DietProfileRecord
from ..schemas.profile import BodyProfileRequest, BodyWeightTargetRequest, BodyWeightRequest


def create_profile_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.get("/api/body-profile")
    def get_body_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
        """读取当前身体档案和最近体重变化；本机单用户演示不要求先完成筛查。"""
        with SessionLocal() as db:
            profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            history = db.scalars(
                select(BodyWeightHistoryRecord).where(BodyWeightHistoryRecord.user_id == user_id).order_by(BodyWeightHistoryRecord.recorded_on.desc()).limit(12)
            ).all()
            if profile is None:
                legacy = db.get(DietProfileRecord, user_id)
                return {
                    "profile": None,
                    "weight_history": [],
                    "legacy_demographics": {
                        "age_years": legacy.age_years if legacy else None,
                        "biological_sex": legacy.biological_sex if legacy else None,
                    },
                }
            serialized = {
                "age_band": profile.age_band,
                "age_years": profile.age_years,
                "biological_sex": profile.biological_sex,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "target_weight_kg": profile.target_weight_kg,
                "updated_at": profile.updated_at.isoformat(),
            }
            weights = [{"date": row.recorded_on.isoformat(), "weight_kg": row.weight_kg} for row in history]
        return {"profile": serialized, "weight_history": weights}

    @router.post("/api/body-weight")
    def save_body_weight(payload: BodyWeightRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        """单独记录今日体重，并同步更新当前档案中的体重。"""
        today = date.today()
        with SessionLocal() as db:
            profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            if profile is None:
                raise HTTPException(status_code=409, detail="请先填写身体档案，再记录体重。")
            record = db.get(BodyWeightHistoryRecord, (user_id, today))
            if record is None:
                db.add(BodyWeightHistoryRecord(user_id=user_id, recorded_on=today, weight_kg=payload.weight_kg))
            else:
                record.weight_kg = payload.weight_kg
            profile.weight_kg = payload.weight_kg
            db.commit()
        return {"ok": True, "recorded_on": today.isoformat(), "weight_kg": payload.weight_kg, "message": "今日体重已记录。"}

    @router.put("/api/body-profile")
    def save_body_profile(payload: BodyProfileRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        """保存最新身体档案，并按日期保留体重记录。"""
        with SessionLocal() as db:
            values = payload.model_dump()
            age = payload.age_years
            values["age_band"] = (
                "under_18" if age < 18 else
                "18_29" if age < 30 else
                "30_44" if age < 45 else
                "45_59" if age < 60 else "60_plus"
            )
            profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            if profile is None:
                profile = BodyProfileRecord(user_id=user_id, **values)
                db.add(profile)
            else:
                for field, value in values.items():
                    setattr(profile, field, value)
            # These legacy fields are no longer collected or used by the app.
            profile.body_fat_percent = None
            profile.waist_cm = None
            # Clear the old copies after moving them to the single source of truth.
            legacy_diet_profile = db.get(DietProfileRecord, user_id)
            if legacy_diet_profile is not None:
                legacy_diet_profile.age_years = None
                legacy_diet_profile.biological_sex = None
            today_weight = db.get(BodyWeightHistoryRecord, (user_id, date.today()))
            if today_weight is None:
                db.add(BodyWeightHistoryRecord(user_id=user_id, recorded_on=date.today(), weight_kg=payload.weight_kg))
            else:
                today_weight.weight_kg = payload.weight_kg
            db.commit()
            db.refresh(profile)
            updated_at = profile.updated_at.isoformat()
        return {"ok": True, "updated_at": updated_at, "message": "个人身体档案已保存；体重变化按日期记录。"}

    @router.put("/api/body-profile/target-weight")
    def save_body_weight_target(payload: BodyWeightTargetRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        """单独保存或清除用户自设体重目标。"""
        with SessionLocal() as db:
            profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            if profile is None:
                raise HTTPException(status_code=409, detail="请先填写身体档案，再设置体重目标。")
            profile.target_weight_kg = payload.target_weight_kg
            db.commit()
        message = "体重目标已清除。" if payload.target_weight_kg is None else "体重目标已保存。"
        return {"ok": True, "target_weight_kg": payload.target_weight_kg, "message": message}

    @router.delete("/api/body-profile")
    def delete_body_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
        """删除身体档案及其体重历史，不删除训练计划和其他训练记录。"""
        with SessionLocal() as db:
            profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            if profile is not None:
                db.delete(profile)
            db.query(BodyWeightHistoryRecord).filter(BodyWeightHistoryRecord.user_id == user_id).delete(synchronize_session=False)
            db.commit()
        return {"ok": True, "message": "个人身体档案和体重历史已删除。"}

    return router
