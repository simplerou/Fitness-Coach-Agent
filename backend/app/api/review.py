"""HTTP endpoints for review."""
from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from ..database import (BodyWeightHistoryRecord, DailySignalRecord, DailyWaterRecord,
    DietDayReviewRecord, DietMealRecord, TrainingLogRecord, WeeklyPlanRecord)
from ..services.plan_service import serialize_today_schedule
from ..services.profile_service import get_registration_date


def create_review_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.get("/api/review/week")
    def weekly_review(week_of: date | None = None, user_id: int = Depends(authenticated_user_id)) -> dict:
        """Return a calendar-week summary; missing entries remain explicitly unknown."""
        selected_date = week_of or date.today()
        monday = selected_date - timedelta(days=selected_date.weekday())
        sunday = monday + timedelta(days=6)
        with SessionLocal() as db:
            registration_date = get_registration_date(db, user_id)
            if sunday < registration_date:
                raise HTTPException(status_code=422, detail="所选周早于本地档案起始日期，无法查看该周记录。")
            signals = db.scalars(
                select(DailySignalRecord)
                .where(
                    DailySignalRecord.user_id == user_id,
                    DailySignalRecord.signal_date >= max(monday, registration_date),
                    DailySignalRecord.signal_date <= sunday,
                )
                .order_by(DailySignalRecord.signal_date)
            ).all()
            logs = db.scalars(
                select(TrainingLogRecord)
                .where(
                    TrainingLogRecord.user_id == user_id,
                    TrainingLogRecord.training_date >= max(monday, registration_date),
                    TrainingLogRecord.training_date <= sunday,
                )
                .order_by(TrainingLogRecord.training_date, TrainingLogRecord.id)
            ).all()
            plan_record = db.scalar(select(WeeklyPlanRecord).where(
                WeeklyPlanRecord.user_id == user_id,
                WeeklyPlanRecord.week_start == monday,
            ))
            plan_data = plan_record.plan_data if plan_record is not None else None
            range_start = max(monday, registration_date)
            diet_meals = db.scalars(select(DietMealRecord).where(
                DietMealRecord.user_id == user_id,
                DietMealRecord.log_date >= range_start,
                DietMealRecord.log_date <= sunday,
            ).order_by(DietMealRecord.log_date, DietMealRecord.id)).all()
            water_records = db.scalars(select(DailyWaterRecord).where(
                DailyWaterRecord.user_id == user_id,
                DailyWaterRecord.log_date >= range_start,
                DailyWaterRecord.log_date <= sunday,
            )).all()
            diet_reviews = db.scalars(select(DietDayReviewRecord).where(
                DietDayReviewRecord.user_id == user_id,
                DietDayReviewRecord.log_date >= range_start,
                DietDayReviewRecord.log_date <= sunday,
            )).all()
            weights = db.scalars(select(BodyWeightHistoryRecord).where(
                BodyWeightHistoryRecord.user_id == user_id,
                BodyWeightHistoryRecord.recorded_on >= range_start,
                BodyWeightHistoryRecord.recorded_on <= sunday,
            ).order_by(BodyWeightHistoryRecord.recorded_on)).all()

        signals_by_day = {record.signal_date: record for record in signals}
        logs_by_day: dict[date, list[TrainingLogRecord]] = {}
        for record in logs:
            logs_by_day.setdefault(record.training_date, []).append(record)
        diet_by_day: dict[date, list[DietMealRecord]] = {}
        for record in diet_meals:
            diet_by_day.setdefault(record.log_date, []).append(record)
        water_by_day = {record.log_date: record.amount_ml for record in water_records}
        diet_review_by_day = {record.log_date: record.complete for record in diet_reviews}
        weight_by_day = {record.recorded_on: record.weight_kg for record in weights}

        completion_counts = {"completed": 0, "partial": 0, "skipped": 0}
        rpe_values = []
        for record in logs:
            completion_counts[record.completion] += 1
            if record.rpe is not None:
                rpe_values.append(record.rpe)

        raw_weekdays = plan_data.get("training_weekdays") if isinstance(plan_data, dict) else None
        planned_weekdays = {
            weekday for weekday in raw_weekdays
            if type(weekday) is int and 1 <= weekday <= 7
        } if isinstance(raw_weekdays, list) else set()
        planned_counts = {"completed": 0, "partial": 0, "skipped": 0, "unlogged": 0}
        planned_date_set = {
            monday + timedelta(days=weekday - 1)
            for weekday in planned_weekdays
            if monday + timedelta(days=weekday - 1) >= registration_date
        }
        # Logs keep their original plan association if the user later regenerates that week's plan.
        planned_date_set.update(
            record.training_date
            for record in logs
            if record.training_date >= registration_date and record.planned_session_title
        )
        planned_dates = sorted(planned_date_set)
        planned_elapsed_dates = []
        for planned_date in planned_dates:
            day_logs = logs_by_day.get(planned_date, [])
            if planned_date > date.today() or (planned_date == date.today() and not day_logs):
                continue
            planned_elapsed_dates.append(planned_date)
            if any(log.completion == "completed" for log in day_logs):
                planned_counts["completed"] += 1
            elif any(log.completion == "partial" for log in day_logs):
                planned_counts["partial"] += 1
            elif any(log.completion == "skipped" for log in day_logs):
                planned_counts["skipped"] += 1
            else:
                planned_counts["unlogged"] += 1

        plan_sessions = plan_data.get("sessions", []) if isinstance(plan_data, dict) else []
        sessions_by_weekday = {
            item.get("weekday"): item
            for item in plan_sessions
            if isinstance(item, dict) and type(item.get("weekday")) is int
        } if isinstance(plan_sessions, list) else {}

        days = []
        for offset in range(7):
            day = monday + timedelta(days=offset)
            signal = signals_by_day.get(day)
            day_logs = logs_by_day.get(day, [])
            planned_item = sessions_by_weekday.get(day.isoweekday())
            saved_log_title = next(
                (record.planned_session_title for record in reversed(day_logs) if record.planned_session_title),
                None,
            )
            planned_title = saved_log_title or (planned_item.get("title") if planned_item else None)
            day_schedule = serialize_today_schedule(plan_data, day)
            day_meals = diet_by_day.get(day, [])
            def sum_logged(field: str) -> float | None:
                values = [getattr(item, field) for item in day_meals if getattr(item, field) is not None]
                return round(sum(values), 1) if values else None
            days.append({
                "date": day.isoformat(),
                "before_registration": day < registration_date,
                "plan_status": "training" if saved_log_title else day_schedule["status"],
                "planned_session_title": planned_title,
                "is_planned_training_day": day in planned_dates,
                "signal": None if signal is None else {
                    "readiness": signal.readiness,
                    "sleep_hours": signal.sleep_hours,
                    "resting_hr": signal.resting_hr,
                },
                "logs": [{
                    "completion": record.completion,
                    "rpe": record.rpe,
                    "skip_reason": record.skip_reason,
                    "note": record.note,
                    "planned_session_title": record.planned_session_title,
                } for record in day_logs],
                "diet": {
                    "meals": [{
                        "meal_type": item.meal_type,
                        "description": item.description,
                    } for item in day_meals],
                    "meal_count": len(day_meals),
                    "calories_kcal": sum_logged("calories_kcal"),
                    "calories_logged_count": sum(item.calories_kcal is not None for item in day_meals),
                    "protein_g": sum_logged("protein_g"),
                    "protein_logged_count": sum(item.protein_g is not None for item in day_meals),
                    "carbs_g": sum_logged("carbs_g"),
                    "carbs_logged_count": sum(item.carbs_g is not None for item in day_meals),
                    "fat_g": sum_logged("fat_g"),
                    "fat_logged_count": sum(item.fat_g is not None for item in day_meals),
                    "water_ml": water_by_day.get(day),
                    "complete": diet_review_by_day.get(day),
                },
                "weight_kg": weight_by_day.get(day),
            })

        return {
            "week_start": monday.isoformat(),
            "week_end": sunday.isoformat(),
            "registration_date": registration_date.isoformat(),
            "summary": {
                "session_count": len(logs),
                "completed_count": completion_counts["completed"],
                "partial_count": completion_counts["partial"],
                "skipped_count": completion_counts["skipped"],
                "average_rpe": round(sum(rpe_values) / len(rpe_values), 1) if rpe_values else None,
                "rpe_count": len(rpe_values),
                "planned_day_count": len(planned_dates),
                "planned_elapsed_day_count": len(planned_elapsed_dates),
                "planned_completed_count": planned_counts["completed"],
                "planned_partial_count": planned_counts["partial"],
                "planned_skipped_count": planned_counts["skipped"],
                "planned_unlogged_count": planned_counts["unlogged"],
                "diet_meal_count": len(diet_meals),
                "diet_days_with_meals": len(diet_by_day),
                "diet_days_marked_complete": sum(bool(value) for value in diet_review_by_day.values()),
                "diet_water_days_logged": len(water_by_day),
                "diet_water_total_ml": sum(water_by_day.values()) if water_by_day else None,
                "weight_days_logged": len(weight_by_day),
            },
            "days": days,
        }

    return router
