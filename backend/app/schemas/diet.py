"""diet ???????"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class DietMealRequest(BaseModel):
    log_date: date = Field(default_factory=date.today)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    description: str = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=240)
    portion: str | None = Field(default=None, max_length=120)
    eaten_at: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    calories_kcal: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=500)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=500)
    nutrition_source: Literal["label", "estimate"] | None = None

    @model_validator(mode="after")
    def trim_description(self):
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("请填写餐食内容。")
        if self.note is not None:
            self.note = self.note.strip() or None
        if self.portion is not None:
            self.portion = self.portion.strip() or None
        if any(value is not None for value in (self.calories_kcal, self.protein_g, self.carbs_g, self.fat_g)) and self.nutrition_source is None:
            raise ValueError("填写营养数据时，请注明来自包装标签还是估算。")
        return self


class DietProfileRequest(BaseModel):
    goal: Literal["fat_loss", "muscle_gain", "maintain", "body_shape", "performance"] | None = None
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None
    training_type: Literal["strength", "cardio", "mixed", "other"] | None = None
    training_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    training_end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    dietary_preference: str | None = Field(default=None, max_length=48)
    allergies: str | None = Field(default=None, max_length=500)
    allergies_reviewed: bool = False
    avoid_foods: str | None = Field(default=None, max_length=500)
    medical_conditions: str | None = Field(default=None, max_length=500)
    injuries: str | None = Field(default=None, max_length=500)
    health_reviewed: bool = False
    cooking_access: Literal["none", "basic", "full"] | None = None
    eating_out_per_week: int | None = Field(default=None, ge=0, le=21)
    budget_note: str | None = Field(default=None, max_length=160)
    water_target_ml: int | None = Field(default=None, ge=500, le=6000)

    @model_validator(mode="after")
    def validate_training_time(self):
        if self.training_time and self.training_end_time:
            start = datetime.strptime(self.training_time, "%H:%M")
            end = datetime.strptime(self.training_end_time, "%H:%M")
            if end <= start:
                raise ValueError("训练结束时间必须晚于开始时间。")
        elif self.training_end_time and not self.training_time:
            raise ValueError("请同时填写训练开始时间。")
        for field in ("dietary_preference", "allergies", "avoid_foods", "medical_conditions", "injuries", "budget_note"):
            value = getattr(self, field)
            if value is not None:
                cleaned = value.strip() or None
                if field == "medical_conditions" and cleaned and cleaned.lower() in ("无", "没有", "无已知疾病", "none", "no"):
                    cleaned = None
                setattr(self, field, cleaned)
        return self


class DietPlanGenerationRequest(BaseModel):
    privacy_consent: Literal[True]


class WaterIntakeRequest(BaseModel):
    log_date: date = Field(default_factory=date.today)
    amount_ml: int = Field(ge=50, le=3000)
