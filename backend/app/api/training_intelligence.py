"""训练智能闭环接口。旧训练日志接口保持兼容。"""
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from ..database import SessionLocal, TrainingLogRecord, TrainingPreferencesRecord, WeeklyPlanRecord
from ..models.training_intelligence import (
    ExerciseAdviceRecord, ExerciseLibraryRecord, PlanAdjustmentRecord,
    RecoveryCheckinRecord, TrainingExerciseEntryRecord,
)
from ..schemas.training_intelligence import AdjustmentDecisionInput, AdviceDecisionInput, SmartTrainingLogInput
from ..services.coach_plan import compute_plan_adjustment, consecutive_weeks
from ..services.progressive_overload import progression_recommendation
from ..services.recovery_service import assess_recovery


def exercise_dict(row: ExerciseLibraryRecord) -> dict:
    return {key: getattr(row, key) for key in (
        "id", "slug", "name", "category", "target_muscles", "equipment", "cues",
        "common_errors", "regressions", "progressions", "alternatives", "demo_images",
        "demo_video_url", "media_credit", "media_license", "media_source_url",
    )}


def advice_dict(row: ExerciseAdviceRecord, exercise: ExerciseLibraryRecord) -> dict:
    return {"id": row.id, "exercise_id": row.exercise_id, "exercise_name": exercise.name,
            "advice_type": row.advice_type, "prescription": row.prescription, "evidence": row.evidence,
            "reason": row.reason, "status": row.status, "created_at": row.created_at.isoformat()}


def create_training_intelligence_router(authenticate: Callable,
                                        get_registration_date: Callable, schedule_for_day: Callable,
                                        week_start_for: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/training", tags=["训练智能"])

    @router.get("/exercises")
    def list_exercises(q: str = "", muscle: str = "", equipment: str = "",
                       user_id: int = Depends(authenticate)) -> dict:
        del user_id
        with SessionLocal() as db:
            rows = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.category, ExerciseLibraryRecord.id)).all()
        query = q.strip().lower()
        items = [exercise_dict(row) for row in rows if
                 (not query or query in row.name.lower() or query in row.slug.lower() or any(query in value.lower() for value in row.target_muscles))
                 and (not muscle or muscle == row.category or muscle in row.target_muscles)
                 and (not equipment or equipment in row.equipment)]
        return {"items": items, "total": len(items)}

    @router.get("/exercises/{exercise_id}")
    def get_exercise(exercise_id: int, user_id: int = Depends(authenticate)) -> dict:
        del user_id
        with SessionLocal() as db:
            row = db.get(ExerciseLibraryRecord, exercise_id)
            if row is None:
                raise HTTPException(404, "未找到该动作。")
            return exercise_dict(row)

    @router.post("/logs")
    def create_smart_log(payload: SmartTrainingLogInput, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            if payload.training_date < get_registration_date(db, user_id):
                raise HTTPException(422, "训练日期早于本地档案起始日期，不能保存该记录。")
            exercise_ids = {item.exercise_id for item in payload.exercises}
            exercises = {row.id: row for row in db.scalars(select(ExerciseLibraryRecord).where(ExerciseLibraryRecord.id.in_(exercise_ids))).all()}
            if len(exercises) != len(exercise_ids):
                raise HTTPException(422, "训练动作中包含无效的动作编号。")
            plan_row = db.get(WeeklyPlanRecord, (user_id, week_start_for(payload.training_date)))
            schedule = schedule_for_day(plan_row.plan_data if plan_row else None, payload.training_date)
            session = schedule.get("session") if schedule.get("status") == "training" else None
            planned_title = session.get("title") if isinstance(session, dict) else None
            log = TrainingLogRecord(user_id=user_id, training_date=payload.training_date, completion=payload.completion,
                                    rpe=payload.rpe, skip_reason=payload.skip_reason, note=payload.note,
                                    planned_session_title=planned_title)
            db.add(log)
            db.flush()
            entries = []
            for item in payload.exercises:
                entry = TrainingExerciseEntryRecord(user_id=user_id, log_id=log.id, **item.model_dump())
                db.add(entry)
                entries.append(entry)
            db.flush()
            recovery_result = None
            warning = "none"
            if payload.recovery:
                prior = db.scalars(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id,
                    TrainingLogRecord.training_date < payload.training_date).order_by(TrainingLogRecord.training_date.desc()).limit(2)).all()
                declined = payload.completion == "partial" or (payload.rpe or 0) >= 9 or any(row.completion == "partial" for row in prior)
                recovery_result = assess_recovery(payload.recovery.model_dump(), declined)
                warning = payload.recovery.warning_symptom
                db.add(RecoveryCheckinRecord(user_id=user_id, log_id=log.id, checkin_date=payload.training_date,
                    **payload.recovery.model_dump(), status=recovery_result["status"], message=recovery_result["message"]))
            pref = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
            generated = []
            if recovery_result is None or recovery_result["allow_progression"]:
                for entry in entries:
                    history_rows = db.execute(select(TrainingExerciseEntryRecord, TrainingLogRecord).join(
                        TrainingLogRecord, TrainingLogRecord.id == TrainingExerciseEntryRecord.log_id).where(
                        TrainingExerciseEntryRecord.user_id == user_id,
                        TrainingExerciseEntryRecord.exercise_id == entry.exercise_id,
                        TrainingExerciseEntryRecord.id != entry.id,
                        TrainingLogRecord.training_date <= payload.training_date,
                    ).order_by(TrainingLogRecord.training_date.desc(), TrainingExerciseEntryRecord.id.desc()).limit(2)).all()
                    history = [{"training_date": row.training_date, "sets": item.sets, "reps": item.reps,
                                "target_reps_min": item.target_reps_min, "target_reps_max": item.target_reps_max,
                                "weight_kg": item.weight_kg, "rpe": item.rpe, "completion": item.completion}
                               for item, row in history_rows]
                    current = {"training_date": payload.training_date, "sets": entry.sets, "reps": entry.reps,
                               "target_reps_min": entry.target_reps_min, "target_reps_max": entry.target_reps_max,
                               "weight_kg": entry.weight_kg, "rpe": entry.rpe, "completion": entry.completion}
                    last = db.scalar(select(ExerciseAdviceRecord).where(ExerciseAdviceRecord.user_id == user_id,
                        ExerciseAdviceRecord.exercise_id == entry.exercise_id).order_by(ExerciseAdviceRecord.created_at.desc()))
                    recommendation = progression_recommendation([current, *history], pref.experience_level if pref else "beginner",
                        last.created_at.date() if last else None, warning)
                    if recommendation:
                        advice = ExerciseAdviceRecord(user_id=user_id, log_id=log.id, exercise_id=entry.exercise_id, **recommendation)
                        db.add(advice); db.flush()
                        generated.append(advice_dict(advice, exercises[entry.exercise_id]))
            db.commit()
            return {"ok": True, "log_id": log.id, "message": "训练记录与恢复信息已保存。",
                    "recovery": recovery_result, "advice": generated}

    @router.get("/logs")
    def detailed_logs(limit: int = Query(default=20, ge=1, le=100), user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            logs = db.scalars(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id)
                              .order_by(TrainingLogRecord.training_date.desc(), TrainingLogRecord.id.desc()).limit(limit)).all()
            result = []
            for log in logs:
                entries = db.scalars(select(TrainingExerciseEntryRecord).where(TrainingExerciseEntryRecord.log_id == log.id)).all()
                recovery = db.scalar(select(RecoveryCheckinRecord).where(RecoveryCheckinRecord.log_id == log.id))
                advices = db.scalars(select(ExerciseAdviceRecord).where(ExerciseAdviceRecord.log_id == log.id)).all()
                exercise_map = {row.id: row for row in db.scalars(select(ExerciseLibraryRecord).where(
                    ExerciseLibraryRecord.id.in_({item.exercise_id for item in [*entries, *advices]}))).all()} if entries or advices else {}
                result.append({"id": log.id, "training_date": log.training_date.isoformat(), "completion": log.completion,
                    "rpe": log.rpe, "skip_reason": log.skip_reason, "note": log.note, "planned_session_title": log.planned_session_title,
                    "exercises": [{"id": item.id, "exercise_id": item.exercise_id, "exercise_name": exercise_map[item.exercise_id].name,
                        "sets": item.sets, "reps": item.reps, "target_reps_min": item.target_reps_min,
                        "target_reps_max": item.target_reps_max, "weight_kg": item.weight_kg, "rpe": item.rpe,
                        "completion": item.completion} for item in entries],
                    "recovery": None if recovery is None else {key: getattr(recovery, key) for key in
                        ("soreness", "sleep_hours", "sleep_quality", "energy", "is_sick", "warning_symptom", "note", "status", "message")},
                    "advice": [advice_dict(item, exercise_map[item.exercise_id]) for item in advices]})
        return {"items": result}

    @router.put("/advice/{advice_id}")
    def decide_advice(advice_id: int, payload: AdviceDecisionInput, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.get(ExerciseAdviceRecord, advice_id)
            if row is None or row.user_id != user_id:
                raise HTTPException(404, "未找到该进阶建议。")
            if row.status != "pending":
                raise HTTPException(409, "该建议已经处理。")
            row.status = payload.decision; row.resolved_at = datetime.now(timezone.utc); db.commit()
        return {"ok": True, "status": payload.decision, "message": "已采纳进阶建议。" if payload.decision == "adopted" else "已忽略本次建议。"}

    @router.delete("/advice/{advice_id}/decision")
    def reset_advice_decision(advice_id: int, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.get(ExerciseAdviceRecord, advice_id)
            if row is None or row.user_id != user_id:
                raise HTTPException(404, "未找到该进阶建议。")
            row.status = "pending"
            row.resolved_at = None
            db.commit()
        return {"ok": True, "status": "pending", "message": "已撤销本次处理，建议重新回到待确认状态。"}

    @router.get("/recovery/summary")
    def recovery_summary(user_id: int = Depends(authenticate)) -> dict:
        monday = date.today() - timedelta(days=date.today().weekday())
        with SessionLocal() as db:
            rows = db.scalars(select(RecoveryCheckinRecord).where(RecoveryCheckinRecord.user_id == user_id,
                RecoveryCheckinRecord.checkin_date >= monday).order_by(RecoveryCheckinRecord.checkin_date.desc())).all()
        order = {"stop": 4, "insufficient": 3, "rest": 3, "attention": 2, "good": 1}
        worst = max(rows, key=lambda row: order.get(row.status, 0)) if rows else None
        return {"today": next(({"status": row.status, "message": row.message} for row in rows if row.checkin_date == date.today()), None),
                "week": None if worst is None else {"status": worst.status, "message": worst.message, "checkin_count": len(rows)}}

    @router.post("/adjustments/preview")
    def preview_adjustment(week_of: date | None = None, user_id: int = Depends(authenticate)) -> dict:
        selected = week_of or date.today()
        source = selected - timedelta(days=selected.weekday())
        target = source + timedelta(days=7)
        with SessionLocal() as db:
            plan = db.get(WeeklyPlanRecord, (user_id, source))
            if plan is None:
                raise HTTPException(409, "所选周没有可用于复盘的训练计划。")
            recommendation = compute_plan_adjustment(db, user_id, source)
            db.query(PlanAdjustmentRecord).filter(PlanAdjustmentRecord.user_id == user_id,
                PlanAdjustmentRecord.source_week_start == source, PlanAdjustmentRecord.status == "pending").update({"status": "ignored", "resolved_at": datetime.now(timezone.utc)})
            row = PlanAdjustmentRecord(user_id=user_id, source_week_start=source, target_week_start=target, recommendation=recommendation)
            db.add(row); db.commit(); db.refresh(row)
            return {"id": row.id, "source_week_start": source.isoformat(), "target_week_start": target.isoformat(),
                    "status": row.status, "recommendation": recommendation}

    @router.put("/adjustments/{adjustment_id}")
    def decide_adjustment(adjustment_id: int, payload: AdjustmentDecisionInput, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.get(PlanAdjustmentRecord, adjustment_id)
            if row is None or row.user_id != user_id:
                raise HTTPException(404, "未找到该计划调整建议。")
            if row.status != "pending":
                raise HTTPException(409, "该调整建议已经处理。")
            if payload.decision == "adopted":
                plan = db.get(WeeklyPlanRecord, (user_id, row.target_week_start))
                proposed = row.recommendation["proposed_plan"]
                if plan is None:
                    db.add(WeeklyPlanRecord(user_id=user_id, week_start=row.target_week_start, plan_data=proposed))
                else:
                    plan.plan_data = proposed
            row.status = payload.decision; row.resolved_at = datetime.now(timezone.utc); db.commit()
        return {"ok": True, "status": payload.decision,
                "message": "下周计划已按确认的预览保存。" if payload.decision == "adopted" else "已取消本次计划调整。"}

    return router

