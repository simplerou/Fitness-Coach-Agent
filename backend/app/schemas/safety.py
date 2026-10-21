"""safety ???????"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class SafetyCheck(BaseModel):
    completed: bool = False
    no_symptoms: bool = False
    symptoms: list[Literal[
        "chest_pain",
        "fainting",
        "dizziness",
        "severe_joint_pain",
        "other_discomfort",
        "uncertain",
    ]] = Field(default_factory=list)


class SafetyResolution(BaseModel):
    confirmed_recovery: bool = False
    followed_professional_advice: bool = False
