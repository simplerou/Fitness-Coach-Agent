"按登录账号读取必要摘要；不向模型暴露账户标识、照片或自由文本健康备注。"
from datetime import date, timedelta
from sqlalchemy import select
from ..models.user_profile import BodyProfileRecord, BodyWeightHistoryRecord
from ..models.training_log import TrainingLogRecord
from ..models.training_plan import WeeklyPlanRecord
from ..models.training_intelligence import RecoveryCheckinRecord, TrainingExerciseEntryRecord, ExerciseLibraryRecord
from ..models.diet import DietMealRecord, DailyWaterRecord, DietProfileRecord
from ..models.shaping import ShapeMeasurementRecord
from ..models.shaping_intelligence import DietDayAdjustmentRecord
from .diet_targets import calculate_diet_targets
from .plan_service import week_start_for, serialize_today_schedule

class CoachData:
    def __init__(self, db, user_id: int, selected_date: date):
        self.db, self.user_id, self.day = db, user_id, selected_date

    def period(self, days: int):
        return self.day - timedelta(days=days - 1), self.day

    def plan(self, selected_date: str | None = None):
        day = date.fromisoformat(selected_date) if selected_date else self.day
        row = self.db.get(WeeklyPlanRecord, (self.user_id, week_start_for(day)))
        return {"source": "weekly_plans", "date": day.isoformat(),
                "status": "recorded" if row else "not_recorded",
                "plan": row.plan_data if row else None,
                "today_schedule": serialize_today_schedule(row.plan_data if row else None, day)}

    def training(self, days: int = 7):
        start, end = self.period(days)
        logs = self.db.scalars(select(TrainingLogRecord).where(
            TrainingLogRecord.user_id == self.user_id, TrainingLogRecord.training_date.between(start, end))
            .order_by(TrainingLogRecord.training_date, TrainingLogRecord.id).limit(150)).all()
        ids = [row.id for row in logs]
        entries = self.db.execute(select(TrainingExerciseEntryRecord, ExerciseLibraryRecord.name)
            .join(ExerciseLibraryRecord, ExerciseLibraryRecord.id == TrainingExerciseEntryRecord.exercise_id)
            .where(TrainingExerciseEntryRecord.user_id == self.user_id, TrainingExerciseEntryRecord.log_id.in_(ids))
            .order_by(TrainingExerciseEntryRecord.log_id, TrainingExerciseEntryRecord.id).limit(300)).all() if ids else []
        log_dates = {r.id: r.training_date.isoformat() for r in logs}
        rpes = [row.rpe for row in logs if row.rpe is not None]
        return {"source": "training_logs + training_exercise_entries",
                "period_start": start.isoformat(), "period_end": end.isoformat(),
                "status": "recorded" if logs else "not_recorded", "record_count": len(logs),
                "training_days": len({row.training_date for row in logs if row.completion in {"completed", "partial"}}),
                "average_rpe": round(sum(rpes) / len(rpes), 1) if rpes else None,
                "logs": [{"date": r.training_date.isoformat(), "completion": r.completion,
                          "rpe": r.rpe, "title": r.planned_session_title} for r in logs],
                "exercises": [{"date": log_dates[r.log_id], "name": name, "target_reps_min": r.target_reps_min,
                               "target_reps_max": r.target_reps_max, "sets": r.sets, "reps": r.reps, "weight_kg": r.weight_kg,
                               "rpe": r.rpe, "completion": r.completion} for r, name in entries],
                "limits": "最多读取150条日志和300条动作明细；记录缺失不视为休息或正常。"}

    def recovery(self, days: int = 7):
        start, end = self.period(days)
        rows = self.db.scalars(select(RecoveryCheckinRecord).where(
            RecoveryCheckinRecord.user_id == self.user_id, RecoveryCheckinRecord.checkin_date.between(start, end))
            .order_by(RecoveryCheckinRecord.checkin_date.desc(), RecoveryCheckinRecord.id.desc()).limit(100)).all()
        return {"source": "recovery_checkins", "period_start": start.isoformat(), "period_end": end.isoformat(),
                "status": "recorded" if rows else "not_recorded", "record_count": len(rows),
                "records": [{"date": r.checkin_date.isoformat(), "soreness": r.soreness,
                             "sleep_hours": r.sleep_hours, "sleep_quality": r.sleep_quality, "energy": r.energy,
                             "is_sick": r.is_sick, "warning_symptom": r.warning_symptom, "status": r.status} for r in rows]}

    def latest_stop(self):
        # 使用最近恢复记录，避免旧风险永久阻止建议。
        rows = self.recovery(7)["records"]
        return bool(rows and (rows[0]["status"] == "stop" or rows[0]["warning_symptom"] != "none"))

    def diet(self, selected_date: str | None = None):
        day = date.fromisoformat(selected_date) if selected_date else self.day
        body = self.db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == self.user_id))
        profile = self.db.get(DietProfileRecord, self.user_id)
        target = calculate_diet_targets(body, profile)
        rows = self.db.scalars(select(DietMealRecord).where(
            DietMealRecord.user_id == self.user_id, DietMealRecord.log_date == day)).all()
        water = self.db.get(DailyWaterRecord, (self.user_id, day))
        adopted = self.db.get(DietDayAdjustmentRecord, (self.user_id, day))
        # 未填写营养数据单独计数，不把已知小计当作完整摄入。
        nutrients = {}
        for field in ("calories_kcal", "protein_g", "carbs_g", "fat_g"):
            known = [getattr(r, field) for r in rows if getattr(r, field) is not None]
            nutrients[field] = {"recorded_sum": round(sum(known), 1) if known else None,
                                "unknown_meals": len(rows) - len(known)}
        return {"source": "diet_meals + daily_water_intakes + diet_targets", "date": day.isoformat(),
                "status": "recorded" if rows else "not_recorded", "meal_count": len(rows),
                "intake": nutrients, "water_ml": water.amount_ml if water else None,
                "target_status": target["status"], "target": target.get("target"),
                "target_message": target.get("message"), "missing": target.get("missing", []),
                "adopted_day_target": adopted.suggestion if adopted and adopted.status == "adopted" else None}

    def shaping(self, days: int = 56):
        start, end = self.period(days)
        rows = self.db.scalars(select(ShapeMeasurementRecord).where(
            ShapeMeasurementRecord.user_id == self.user_id, ShapeMeasurementRecord.recorded_on.between(start, end))
            .order_by(ShapeMeasurementRecord.recorded_on).limit(84)).all()
        weights = self.db.scalars(select(BodyWeightHistoryRecord).where(
            BodyWeightHistoryRecord.user_id == self.user_id, BodyWeightHistoryRecord.recorded_on.between(start, end))
            .order_by(BodyWeightHistoryRecord.recorded_on).limit(84)).all()
        metrics = ("waist_cm", "hip_cm", "chest_cm", "arm_cm", "thigh_cm", "body_fat_percent", "skeletal_muscle_kg")
        return {"source": "shape_measurements + body_weight_history",
                "period_start": start.isoformat(), "period_end": end.isoformat(),
                "status": "recorded" if rows or weights else "not_recorded",
                "measurements": [{"date": r.recorded_on.isoformat(), "composition_source": r.composition_source,
                                  **{k: getattr(r, k) for k in metrics}} for r in rows],
                "weight_history": [{"date": r.recorded_on.isoformat(), "weight_kg": r.weight_kg} for r in weights]}
