from typing import Literal

from pydantic import BaseModel, Field, model_validator

MuscleGroup = Literal["胸", "背", "腿", "肩", "臂", "核心"]


class ShapingPreferenceInput(BaseModel):
    goal: Literal["whole_body", "glutes_legs", "shoulders_back"] = "whole_body"
    focus_groups: list[MuscleGroup] = Field(default_factory=list, max_length=3)
    excluded_groups: list[MuscleGroup] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def no_overlap(self):
        if set(self.focus_groups) & set(self.excluded_groups):
            raise ValueError("侧重部位与禁忌部位不能重复。")
        return self


class WeakPartDecisionInput(BaseModel):
    decision: Literal["adopted", "ignored"]


class CoachQuestionInput(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    privacy_consent: bool = False


class DietAdjustmentDecisionInput(BaseModel):
    decision: Literal["adopted", "ignored"]
