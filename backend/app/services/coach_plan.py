"从现有训练记录计算周计划调整预览；不保存计划、不提交事务。"
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from ..models.training_log import TrainingLogRecord
from ..models.training_plan import WeeklyPlanRecord, TrainingPreferencesRecord
from ..models.training_intelligence import RecoveryCheckinRecord, TrainingExerciseEntryRecord, ExerciseAdviceRecord, ExerciseLibraryRecord
from .plan_adjustment_service import build_adjustment

def consecutive_weeks(logs: list[TrainingLogRecord], source_week: date) -> int:
    active = {row.training_date - timedelta(days=row.training_date.weekday()) for row in logs if row.completion in {"completed", "partial"}}
    count, cursor = 0, source_week
    while cursor in active:
        count += 1
        cursor -= timedelta(days=7)
    return count


def compute_plan_adjustment(db, user_id, source, as_of=None):
    plan = db.get(WeeklyPlanRecord, (user_id, source))
    if plan is None:
        raise HTTPException(409, "所选周没有可用于复盘的训练计划。")
    end = min(source + timedelta(days=6), as_of) if as_of else source + timedelta(days=6)
    logs = db.scalars(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id,
        TrainingLogRecord.training_date >= source, TrainingLogRecord.training_date <= end)).all()
    recoveries = db.scalars(select(RecoveryCheckinRecord).where(RecoveryCheckinRecord.user_id == user_id,
        RecoveryCheckinRecord.checkin_date >= source, RecoveryCheckinRecord.checkin_date <= end)).all()
    entries = db.scalars(select(TrainingExerciseEntryRecord).join(TrainingLogRecord,
        TrainingLogRecord.id == TrainingExerciseEntryRecord.log_id).where(TrainingExerciseEntryRecord.user_id == user_id,
        TrainingLogRecord.training_date >= source, TrainingLogRecord.training_date <= end)).all()
    advices = db.scalars(select(ExerciseAdviceRecord).join(TrainingLogRecord,
        TrainingLogRecord.id == ExerciseAdviceRecord.log_id).where(ExerciseAdviceRecord.user_id == user_id,
        TrainingLogRecord.training_date >= source, TrainingLogRecord.training_date <= end)).all()
    planned_days = len(plan.plan_data.get("training_weekdays", [])) or 1
    completed = sum(row.completion in {"completed", "partial"} for row in logs)
    if as_of is not None:
        # 手动复盘只评估已到来的计划日，并按日期去重，避免重复补记放大完成率。
        elapsed = {d for d in plan.plan_data.get("training_weekdays", []) if d <= end.isoweekday()}
        if not elapsed:
            raise HTTPException(409, "本周尚无已到来的计划训练日，暂不生成调整草案。")
        recorded_days = {row.training_date for row in logs if row.training_date.isoweekday() in elapsed}
        if not recorded_days:
            raise HTTPException(409, "已到来的计划训练日尚未记录，不能据此判断完成率或生成调整。")
        planned_days = len(recorded_days)
        completed = len({row.training_date for row in logs
            if row.completion in {"completed", "partial"} and row.training_date in recorded_days})
    status_order = {"stop": 4, "insufficient": 3, "rest": 3, "attention": 2, "good": 1}
    worst = max(recoveries, key=lambda row: status_order.get(row.status, 0)).status if recoveries else "unknown"
    history = db.scalars(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id,
        TrainingLogRecord.training_date <= end)).all()
    stats = {"completion_rate": round(completed / planned_days, 2),
        "average_rpe": round(sum(row.rpe for row in logs if row.rpe is not None) / len([row for row in logs if row.rpe is not None]), 1) if any(row.rpe is not None for row in logs) else None,
        "recovery_status": worst, "has_warning_symptom": any(row.warning_symptom != "none" for row in recoveries),
        "tracked_exercises": len({row.exercise_id for row in entries}),
        "progressed_exercises": len({row.exercise_id for row in advices}),
        "consecutive_training_weeks": consecutive_weeks(history, source)}
    planned_exercises = [item for session in plan.plan_data.get("sessions", []) for item in session.get("exercises", [])]
    if stats["tracked_exercises"] and not stats["progressed_exercises"] and planned_exercises:
        current = db.get(ExerciseLibraryRecord, planned_exercises[0].get("id"))
        pref = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
        candidates = db.scalars(select(ExerciseLibraryRecord).where(ExerciseLibraryRecord.category == current.category,
            ExerciseLibraryRecord.id != current.id).order_by(ExerciseLibraryRecord.id)).all() if current else []
        preferred_ids = set(pref.preferred_exercise_ids or []) if pref else set()
        if preferred_ids:
            candidates = [item for item in candidates if item.id in preferred_ids]
        else:
            plan_equipment = set(plan.plan_data.get("equipment", []))
            candidates = [item for item in candidates if plan_equipment.intersection(item.equipment)]
        if candidates:
            replacement = candidates[0]
            stats["replacement"] = {"from": planned_exercises[0], "to": {"id": replacement.id,
                "name": replacement.name, "category": replacement.category, "target_muscles": replacement.target_muscles}}
    recommendation = build_adjustment(plan.plan_data, stats)
    if as_of is not None:
        stats.update({"period_start": source.isoformat(), "period_end": end.isoformat(),
                      "planned_days_evaluated": planned_days, "planned_days_due": len(elapsed),
                      "unrecorded_plan_days": len(elapsed) - len(recorded_days), "week_in_progress": end < source + timedelta(days=6)})
        if stats["unrecorded_plan_days"]:
            recommendation["reasons"].append(f"仍有{stats['unrecorded_plan_days']}个已到来的计划日未记录，完成率只针对已记录计划日，不推断其为跳过。")
        if stats["week_in_progress"] or stats["unrecorded_plan_days"]:
            recommendation["reasons"].append("本周样本尚未完整，只使用截至所选日期已记录的计划日，未到来的训练日未计入完成率。")
            if recommendation["kind"] == "slight_increase":
                recommendation.update(kind="maintain", proposed_plan=plan.plan_data,
                    changed=["本周样本尚未完整，下周先保持当前安排，不据此自动加量"])
    return recommendation
