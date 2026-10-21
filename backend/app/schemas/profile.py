"""profile ???????"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class BodyProfileRequest(BaseModel):
    """校验用户自愿提供的基础身体档案。"""

    age_years: int = Field(ge=13, le=100)
    biological_sex: Literal["female", "male", "unspecified"] | None = None
    height_cm: float = Field(ge=100, le=230)
    weight_kg: float = Field(ge=25, le=300)


class BodyWeightTargetRequest(BaseModel):
    target_weight_kg: float | None = Field(default=None, ge=25, le=300)


class BodyWeightRequest(BaseModel):
    weight_kg: float = Field(ge=25, le=300)
