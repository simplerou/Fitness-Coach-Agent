"""??????????????????"""
from __future__ import annotations

from datetime import date, timedelta
from ..database import TrainingPreferencesRecord, TrainingSchedulePreferencesRecord


def week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def serialize_plan_preferences(
    record: TrainingPreferencesRecord,
    schedule: TrainingSchedulePreferencesRecord,
) -> dict:
    return {
        "goal": record.goal,
        "days_per_week": record.days_per_week,
        "training_weekdays": schedule.weekdays,
        "experience_level": record.experience_level,
        "equipment": record.equipment,
        "session_minutes": record.session_minutes,
        "preferred_exercise_ids": record.preferred_exercise_ids or [],
    }


def serialize_today_schedule(plan_data: dict | None, selected_day: date) -> dict:
    weekday = selected_day.isoweekday()
    if not isinstance(plan_data, dict) or not plan_data:
        return {
            "status": "no_plan",
            "weekday": weekday,
            "session": None,
            "message": "本周还没有保存的计划。",
        }

    training_weekdays = plan_data.get("training_weekdays")
    if (
        not isinstance(training_weekdays, list)
        or not 1 <= len(training_weekdays) <= 6
        or any(type(day) is not int or day < 1 or day > 7 for day in training_weekdays)
        or len(set(training_weekdays)) != len(training_weekdays)
    ):
        return {
            "status": "legacy_plan",
            "weekday": weekday,
            "session": None,
            "message": "本周计划尚无具体星期安排。",
        }

    if weekday not in training_weekdays:
        return {
            "status": "rest",
            "weekday": weekday,
            "session": None,
            "message": "今天是当前周计划中的休息日。",
        }

    sessions = plan_data.get("sessions")
    session = None
    if isinstance(sessions, list):
        session = next(
            (
                item for item in sessions
                if isinstance(item, dict) and item.get("weekday") == weekday
            ),
            None,
        )
    if session is None:
        return {
            "status": "legacy_plan",
            "weekday": weekday,
            "session": None,
            "message": "本周计划中的当天安排无法读取，请前往周计划页查看。",
        }
    return {
        "status": "training",
        "weekday": weekday,
        "session": session,
        "message": "按今天对应的计划安排进行；不要因为本工具的结果临时加量。",
    }
