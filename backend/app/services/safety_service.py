"""???????????????"""
from __future__ import annotations

from datetime import date

SCREENING_DATES: dict[int, date] = {}


SYMPTOM_LABELS = {
    "chest_pain": "胸痛或胸闷",
    "fainting": "晕厥或接近晕厥",
    "dizziness": "明显眩晕",
    "severe_joint_pain": "严重关节疼痛",
    "other_discomfort": "其他明显不适",
    "uncertain": "无法判断是否存在上述情况",
}
