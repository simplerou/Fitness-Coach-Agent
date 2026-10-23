"仅保存用户可确认的草案；pending 状态不改变训练与饮食目标。"
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class CoachActionDraftRecord(Base):
    __tablename__ = "coach_action_drafts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("account_users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    draft_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
