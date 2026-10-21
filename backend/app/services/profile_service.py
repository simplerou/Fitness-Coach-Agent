"""?????????"""
from __future__ import annotations

from datetime import date
from sqlalchemy import select
from ..database import LocalProfileRecord


def get_registration_date(db, user_id: int) -> date:
    profile = db.scalar(select(LocalProfileRecord).where(LocalProfileRecord.user_id == user_id))
    return profile.registered_on if profile else date.today()
