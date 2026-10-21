"""daily_signal ???????"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class DailySignal(BaseModel):
    readiness: Literal["good", "okay", "poor"]
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    resting_hr: int | None = Field(default=None, ge=25, le=240)
