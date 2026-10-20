"""真实测量值、双周提醒与方向无关的目标进度；不推算缺失读数。"""
import base64
import binascii
from datetime import date, timedelta
from io import BytesIO

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from ..database import BodyWeightHistoryRecord
from ..models.shaping import ShapeMeasurementRecord, ShapePhotoRecord, ShapeTargetRecord

CIRCUMFERENCE_METRICS = ("waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm")
METRICS = (*CIRCUMFERENCE_METRICS, "body_fat_percent", "skeletal_muscle_kg")
LABELS = dict(zip(METRICS, ("腰围", "臀围", "胸围", "臂围", "腿围", "体脂率", "骨骼肌")))
RANGES = {"waist_cm": (30, 250), "hip_cm": (40, 250), "chest_cm": (40, 250),
          "arm_cm": (10, 100), "thigh_cm": (20, 150), "body_fat_percent": (3, 65)}


def progress_percent(baseline: float, target: float, current: float) -> float:
    if target == baseline:
        return 100.0 if current == target else 0.0
    return round(max(0, min(100, (current - baseline) / (target - baseline) * 100)), 1)


def measurement_rows(db, user_id: int):
    return db.scalars(select(ShapeMeasurementRecord).where(
        ShapeMeasurementRecord.user_id == user_id
    ).order_by(ShapeMeasurementRecord.recorded_on)).all()


def target_data(target, rows) -> dict:
    readings = [row for row in rows if row.recorded_on >= target.baseline_date and getattr(row, target.metric) is not None]
    latest = readings[-1] if readings else None
    value = getattr(latest, target.metric) if latest else None
    progress = progress_percent(target.baseline_value, target.target_value, value) if value is not None else None
    return {"metric": target.metric, "baseline_value": target.baseline_value,
            "baseline_date": target.baseline_date.isoformat(), "target_value": target.target_value,
            "current_value": value, "current_date": latest.recorded_on.isoformat() if latest else None,
            "progress_percent": progress, "milestones": target.milestones}


def unlock_milestones(db, user_id: int) -> list[str]:
    rows = measurement_rows(db, user_id)
    messages = []
    for target in db.scalars(select(ShapeTargetRecord).where(ShapeTargetRecord.user_id == user_id)):
        progress = target_data(target, rows)["progress_percent"]
        earned = [step for step in (25, 50, 75, 100) if progress is not None and progress >= step and step not in target.milestones]
        if earned:
            target.milestones = sorted(set(target.milestones + earned))
            messages.append(f"{LABELS[target.metric]}目标已解锁 {max(earned)}% 里程碑。")
    return messages


def dashboard(db, user_id: int) -> dict:
    rows = measurement_rows(db, user_id)
    weights = db.scalars(select(BodyWeightHistoryRecord).where(
        BodyWeightHistoryRecord.user_id == user_id).order_by(BodyWeightHistoryRecord.recorded_on)).all()
    by_date = {row.recorded_on: row.weight_kg for row in weights}
    serialized = [{"recorded_on": row.recorded_on.isoformat(), **{key: getattr(row, key) for key in METRICS},
                   "composition_source": row.composition_source, "weight_kg": by_date.get(row.recorded_on)} for row in rows]
    reminders = []
    for metric in CIRCUMFERENCE_METRICS:
        latest = next((row for row in reversed(rows) if getattr(row, metric) is not None), None)
        due = latest.recorded_on + timedelta(days=14) if latest else None
        reminders.append({"metric": metric, "last_measured_on": latest.recorded_on.isoformat() if latest else None,
                          "next_due_on": due.isoformat() if due else None, "due": due is not None and due <= date.today()})
    photos = db.execute(select(ShapePhotoRecord.id, ShapePhotoRecord.recorded_on, ShapePhotoRecord.view, ShapePhotoRecord.updated_at)
                        .where(ShapePhotoRecord.user_id == user_id)
                        .order_by(ShapePhotoRecord.recorded_on, ShapePhotoRecord.view)).all()
    return {"today": date.today().isoformat(), "measurements": serialized,
            "weight_history": [{"date": row.recorded_on.isoformat(), "weight_kg": row.weight_kg} for row in weights],
            "reminders": reminders,
            "targets": [target_data(target, rows) for target in db.scalars(select(ShapeTargetRecord).where(ShapeTargetRecord.user_id == user_id))],
            "photos": [{"id": row.id, "recorded_on": row.recorded_on.isoformat(), "view": row.view,
                        "updated_at": row.updated_at.isoformat()} for row in photos]}


def normalize_photo(data_url: str) -> bytes:
    """验证并重新编码照片，移除 EXIF/GPS；数据库只保存 JPEG，不托管原始文件。"""
    header, separator, encoded = data_url.partition(",")
    if not separator or header not in ("data:image/jpeg;base64", "data:image/png;base64", "data:image/webp;base64"):
        raise HTTPException(422, "请选择 JPG、PNG 或 WebP 图片。")
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 4 * 1024 * 1024:
            raise HTTPException(422, "照片过大，请压缩到 4 MB 以内。")
        with Image.open(BytesIO(raw)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP") or image.width * image.height > 24_000_000:
                raise HTTPException(422, "图片尺寸过大或格式不支持，请更换照片。")
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((1600, 1600))
            output = BytesIO()
            image.save(output, format="JPEG", quality=88)
            return output.getvalue()
    except (ValueError, binascii.Error, OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise HTTPException(422, "图片无法读取，请重新选择有效照片。") from error
