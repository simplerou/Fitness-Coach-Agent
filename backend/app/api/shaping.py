"""塑型扩展接口；复用现有签名 Cookie 验证，不改动训练与饮食接口。"""
from datetime import date
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from ..database import SessionLocal
from ..models.shaping import ShapeMeasurementRecord, ShapePhotoRecord, ShapeTargetRecord
from ..schemas.shaping import ShapeMeasurementRequest, ShapeMetric, ShapePhotoRequest, ShapeTargetRequest
from ..services.shaping_service import RANGES, dashboard, measurement_rows, normalize_photo, unlock_milestones


def past_or_today(day: date) -> None:
    if day > date.today():
        raise HTTPException(422, "不能记录未来日期的身体数据或照片。")


def create_shaping_router(authenticate: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/shaping", tags=["塑型"])

    @router.get("")
    def get_dashboard(user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            return dashboard(db, user_id)

    @router.put("/measurement")
    def save_measurement(payload: ShapeMeasurementRequest, user_id: int = Depends(authenticate)) -> dict:
        past_or_today(payload.recorded_on)
        with SessionLocal() as db:
            row = db.get(ShapeMeasurementRecord, (user_id, payload.recorded_on))
            if row is None:
                row = ShapeMeasurementRecord(user_id=user_id, recorded_on=payload.recorded_on)
                db.add(row)
            for field, value in payload.model_dump(exclude={"recorded_on"}).items():
                setattr(row, field, value)
            db.flush()
            messages = unlock_milestones(db, user_id)
            db.commit()
        return {"ok": True, "message": "测量数据已保存，同一天的记录已更新。", "milestone_messages": messages}

    @router.delete("/measurement/{recorded_on}")
    def delete_measurement(recorded_on: date, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.get(ShapeMeasurementRecord, (user_id, recorded_on))
            if row is None:
                raise HTTPException(404, "未找到这一天的测量记录。")
            db.delete(row)
            db.commit()
        return {"ok": True, "message": "测量记录已删除。"}

    @router.put("/target")
    def save_target(payload: ShapeTargetRequest, user_id: int = Depends(authenticate)) -> dict:
        low, high = RANGES[payload.metric]
        if not low <= payload.target_value <= high:
            raise HTTPException(422, f"目标数值需在 {low}–{high} 之间。")
        with SessionLocal() as db:
            latest = next((row for row in reversed(measurement_rows(db, user_id)) if getattr(row, payload.metric) is not None), None)
            if latest is None:
                raise HTTPException(409, "请先记录该指标的测量值，再设置目标。")
            baseline = getattr(latest, payload.metric)
            if payload.target_value == baseline:
                raise HTTPException(422, "目标与当前测量值相同，请设置不同的目标。")
            target = db.get(ShapeTargetRecord, (user_id, payload.metric))
            if target is None:
                target = ShapeTargetRecord(user_id=user_id, metric=payload.metric)
                db.add(target)
            # 修改目标时以当前读数重新开始，避免继承旧目标的进度。
            target.baseline_value = baseline
            target.baseline_date = latest.recorded_on
            target.target_value = payload.target_value
            target.milestones = []
            db.commit()
        return {"ok": True, "message": "目标已保存，将从当前测量值开始追踪。"}

    @router.delete("/target/{metric}")
    def delete_target(metric: ShapeMetric, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            target = db.get(ShapeTargetRecord, (user_id, metric))
            if target is not None:
                db.delete(target)
                db.commit()
        return {"ok": True, "message": "目标已清除，测量记录仍保留。"}

    @router.put("/photo")
    def save_photo(payload: ShapePhotoRequest, user_id: int = Depends(authenticate)) -> dict:
        past_or_today(payload.recorded_on)
        image_data = normalize_photo(payload.image_data)
        with SessionLocal() as db:
            row = db.scalar(select(ShapePhotoRecord).where(ShapePhotoRecord.user_id == user_id,
                ShapePhotoRecord.recorded_on == payload.recorded_on, ShapePhotoRecord.view == payload.view))
            if row is None:
                row = ShapePhotoRecord(user_id=user_id, recorded_on=payload.recorded_on, view=payload.view)
                db.add(row)
            row.image_data = image_data
            db.commit()
        return {"ok": True, "message": "照片已保存，同一天同一视角的照片已替换。"}

    @router.get("/photo/{photo_id}/image")
    def get_photo(photo_id: int, user_id: int = Depends(authenticate)) -> Response:
        with SessionLocal() as db:
            row = db.scalar(select(ShapePhotoRecord).where(ShapePhotoRecord.user_id == user_id, ShapePhotoRecord.id == photo_id))
            if row is None:
                raise HTTPException(404, "照片不存在或已删除。")
            return Response(row.image_data, media_type="image/jpeg", headers={
                "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @router.delete("/photo/{photo_id}")
    def delete_photo(photo_id: int, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.scalar(select(ShapePhotoRecord).where(ShapePhotoRecord.user_id == user_id, ShapePhotoRecord.id == photo_id))
            if row is None:
                raise HTTPException(404, "照片不存在或已删除。")
            db.delete(row)
            db.commit()
        return {"ok": True, "message": "照片已删除。"}

    return router
