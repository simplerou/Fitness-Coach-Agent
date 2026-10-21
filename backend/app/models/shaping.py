"""塑型数据独立保存，所有主键/查询均包含账号归属。"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ShapeMeasurementRecord(Base):
    __tablename__ = "shape_measurements"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    recorded_on: Mapped[date] = mapped_column(Date, primary_key=True)
    waist_cm: Mapped[float | None] = mapped_column(Float)
    hip_cm: Mapped[float | None] = mapped_column(Float)
    chest_cm: Mapped[float | None] = mapped_column(Float)
    arm_cm: Mapped[float | None] = mapped_column(Float)
    thigh_cm: Mapped[float | None] = mapped_column(Float)
    body_fat_percent: Mapped[float | None] = mapped_column(Float)
    skeletal_muscle_kg: Mapped[float | None] = mapped_column(Float)
    composition_source: Mapped[str | None] = mapped_column(String(24))


class ShapeTargetRecord(Base):
    __tablename__ = "shape_targets"

    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), primary_key=True)
    metric: Mapped[str] = mapped_column(String(24), primary_key=True)
    baseline_value: Mapped[float] = mapped_column(Float)
    baseline_date: Mapped[date] = mapped_column(Date)
    target_value: Mapped[float] = mapped_column(Float)
    # 已解锁的节点保留，波动后恢复不会反复提醒。
    milestones: Mapped[list[int]] = mapped_column(JSON, default=list)


class ShapePhotoRecord(Base):
    __tablename__ = "shape_photos"
    __table_args__ = (UniqueConstraint("user_id", "recorded_on", "view", name="uq_shape_photo_day_view"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    recorded_on: Mapped[date] = mapped_column(Date, index=True)
    view: Mapped[str] = mapped_column(String(8))
    image_data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
