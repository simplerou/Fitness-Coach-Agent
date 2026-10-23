"教练请求、页面上下文和确认动作的输入契约。"
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class CoachContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: Literal["today", "plan", "log", "diet", "shaping", "review", "library", "profile"] = "today"
    selected_date: date | None = None

class CoachTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)

class CoachQuestionInput(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    privacy_consent: bool = False
    context: CoachContext = Field(default_factory=CoachContext)
    history: list[CoachTurn] = Field(default_factory=list, max_length=6)

class CoachActionDecision(BaseModel):
    decision: Literal["adopted", "ignored"]
