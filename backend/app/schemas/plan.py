"""plan ???????"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class PlanRequest(BaseModel):
    goal: Literal["strength", "fitness", "fat_loss"] = "fitness"
    days_per_week: int = Field(default=3, ge=1, le=6)
    training_weekdays: list[int] | None = None
    experience_level: Literal["beginner", "some_experience", "experienced"] = "beginner"
    equipment: list[Literal["bodyweight_only", "dumbbells", "resistance_bands", "gym"]] = Field(
        default_factory=lambda: ["bodyweight_only"]
    )
    session_minutes: Literal[20, 30, 45, 60] = 30
    preferred_exercise_ids: list[int] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_plan_preferences(self):
        if not self.equipment:
            raise ValueError("请至少选择一种可用器械。")
        if len(set(self.equipment)) != len(self.equipment):
            raise ValueError("器械选项不能重复。")
        if "bodyweight_only" in self.equipment and len(self.equipment) > 1:
            raise ValueError("“仅自重”不能与其他器械同时选择。")
        if self.training_weekdays is not None:
            if not 1 <= len(self.training_weekdays) <= 6:
                raise ValueError("每周必须选择 1 到 6 个训练日。")
            if any(day < 1 or day > 7 for day in self.training_weekdays):
                raise ValueError("训练星期编号必须在 1 到 7 之间。")
            if len(set(self.training_weekdays)) != len(self.training_weekdays):
                raise ValueError("训练星期不能重复。")
            if len(self.training_weekdays) != self.days_per_week:
                raise ValueError("每周训练天数必须与选择的星期数量一致。")
        if len(set(self.preferred_exercise_ids)) != len(self.preferred_exercise_ids):
            raise ValueError("训练动作不能重复选择。")
        return self
