"""training_log ???????"""
from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class TrainingLog(BaseModel):
    training_date: date = Field(default_factory=date.today)
    completion: Literal["completed", "partial", "skipped"]
    rpe: int | None = Field(default=None, ge=1, le=10)
    skip_reason: Literal["no_time", "too_tired", "discomfort", "other"] | None = None
    note: str | None = Field(default=None, max_length=240)
