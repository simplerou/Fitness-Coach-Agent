from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ShapeMetric = Literal["waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm", "body_fat_percent"]
PhotoView = Literal["front", "side", "back"]


class ShapeMeasurementRequest(BaseModel):
    recorded_on: date
    waist_cm: float | None = Field(default=None, ge=30, le=250, allow_inf_nan=False)
    hip_cm: float | None = Field(default=None, ge=40, le=250, allow_inf_nan=False)
    chest_cm: float | None = Field(default=None, ge=40, le=250, allow_inf_nan=False)
    arm_cm: float | None = Field(default=None, ge=10, le=100, allow_inf_nan=False)
    thigh_cm: float | None = Field(default=None, ge=20, le=150, allow_inf_nan=False)
    body_fat_percent: float | None = Field(default=None, ge=3, le=65, allow_inf_nan=False)
    skeletal_muscle_kg: float | None = Field(default=None, ge=5, le=100, allow_inf_nan=False)
    composition_source: Literal["scale_reading", "professional_measurement", "manual"] | None = None

    @model_validator(mode="after")
    def check_measurements(self):
        numeric = self.model_dump(exclude={"recorded_on", "composition_source"})
        if not any(value is not None for value in numeric.values()):
            raise ValueError("请至少填写一项测量数据。")
        has_composition = self.body_fat_percent is not None or self.skeletal_muscle_kg is not None
        if has_composition and self.composition_source is None:
            raise ValueError("请注明体成分数据的来源。")
        if not has_composition:
            self.composition_source = None
        return self


class ShapeTargetRequest(BaseModel):
    metric: ShapeMetric
    target_value: float = Field(gt=0, le=250, allow_inf_nan=False)


class ShapePhotoRequest(BaseModel):
    recorded_on: date
    view: PhotoView
    image_data: str = Field(min_length=30, max_length=5_600_000)
