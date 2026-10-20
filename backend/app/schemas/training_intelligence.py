from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ExerciseEntryInput(BaseModel):
    exercise_id: int
    sets: int = Field(ge=1, le=20)
    reps: int = Field(ge=1, le=100)
    target_reps_min: int = Field(ge=1, le=100)
    target_reps_max: int = Field(ge=1, le=100)
    weight_kg: float = Field(default=0, ge=0, le=1000)
    rpe: int = Field(ge=1, le=10)
    completion: Literal["completed", "partial", "skipped"] = "completed"

    @model_validator(mode="after")
    def validate_range(self):
        if self.target_reps_max < self.target_reps_min:
            raise ValueError("目标次数上限不能小于下限。")
        return self


class RecoveryInput(BaseModel):
    soreness: int = Field(ge=1, le=5)
    sleep_hours: float = Field(ge=0, le=24)
    sleep_quality: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    is_sick: bool = False
    warning_symptom: Literal["none", "joint_pain", "sharp_pain", "swelling"] = "none"
    note: str | None = Field(default=None, max_length=300)


class SmartTrainingLogInput(BaseModel):
    training_date: date
    completion: Literal["completed", "partial", "skipped"]
    rpe: int | None = Field(default=None, ge=1, le=10)
    skip_reason: Literal["no_time", "too_tired", "discomfort", "other"] | None = None
    note: str | None = Field(default=None, max_length=240)
    exercises: list[ExerciseEntryInput] = Field(default_factory=list, max_length=20)
    recovery: RecoveryInput | None = None

    @model_validator(mode="after")
    def validate_log(self):
        if self.completion == "skipped" and self.skip_reason is None:
            raise ValueError("未完成训练时，请选择未完成原因。")
        if self.completion != "skipped" and not self.exercises:
            raise ValueError("请至少记录一个训练动作。")
        return self


class AdviceDecisionInput(BaseModel):
    decision: Literal["adopted", "ignored"]


class AdjustmentDecisionInput(BaseModel):
    decision: Literal["adopted", "ignored"]

