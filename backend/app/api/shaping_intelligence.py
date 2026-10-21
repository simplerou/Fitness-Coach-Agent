"""塑形智能联动层：规则计算、受控 Agent、确认后写回与报告快照。"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from ..database import (BodyProfileRecord, DietProfileRecord, SessionLocal, TrainingLogRecord,
                        TrainingPreferencesRecord, WeeklyPlanRecord)
from ..models.shaping_intelligence import (DietDayAdjustmentRecord, MuscleGroupStatRecord, QaLogRecord,
    ReportSnapshotRecord, ShapingPreferenceRecord, WeakPartAdviceRecord)
from ..models.training_intelligence import (ExerciseKnowledgeDocumentRecord, ExerciseLibraryRecord,
    RecoveryCheckinRecord, TrainingExerciseEntryRecord)
from ..schemas.shaping_intelligence import (CoachQuestionInput, DietAdjustmentDecisionInput,
    ShapingPreferenceInput, WeakPartDecisionInput)
from ..services.muscle_analysis import GOAL_FOCUS, build_addition, calculate_muscle_stats, identify_weak_parts
from ..services.nutrition_link import calculate_day_nutrition
from ..services.shape_report_service import build_shape_report, completed_period
from ..services.exercise_knowledge import EMBEDDING_MODEL, retrieve_documents
from ..services.shaping_agent import answer_coach_question, route_question


def _preference(db, user_id: int) -> ShapingPreferenceRecord:
    row = db.get(ShapingPreferenceRecord, user_id)
    if row is None:
        row = ShapingPreferenceRecord(user_id=user_id, goal="whole_body", focus_groups=[], excluded_groups=[])
        db.add(row); db.flush()
    return row


def _preference_dict(row: ShapingPreferenceRecord) -> dict:
    return {"goal": row.goal, "focus_groups": row.focus_groups, "excluded_groups": row.excluded_groups}


def _exercise_reference(row: ExerciseLibraryRecord) -> dict:
    return {"id": row.id, "slug": row.slug, "name": row.name, "category": row.category,
            "target_muscles": row.target_muscles, "cues": row.cues, "common_errors": row.common_errors,
            "regressions": row.regressions, "progressions": row.progressions, "alternatives": row.alternatives,
            "demo_images": row.demo_images, "demo_video_url": row.demo_video_url}


def create_shaping_intelligence_router(authenticate: Callable, week_start_for: Callable,
                                       schedule_for_day: Callable, calculate_targets: Callable) -> APIRouter:
    router = APIRouter(prefix="/api/shaping/intelligence", tags=["塑形智能联动"])

    @router.get("/preferences")
    def get_preferences(user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = _preference(db, user_id); db.commit()
            return {"preferences": _preference_dict(row)}

    @router.put("/preferences")
    def save_preferences(payload: ShapingPreferenceInput, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = _preference(db, user_id)
            row.goal = payload.goal; row.focus_groups = payload.focus_groups; row.excluded_groups = payload.excluded_groups
            db.commit()
        return {"ok": True, "message": "塑型侧重与禁忌部位已保存。", "preferences": payload.model_dump()}

    @router.post("/weak-parts/analyze")
    def analyze_weak_parts(user_id: int = Depends(authenticate)) -> dict:
        period_end = date.today(); period_start = period_end - timedelta(days=27)
        with SessionLocal() as db:
            preference = _preference(db, user_id)
            rows = db.execute(select(TrainingExerciseEntryRecord, TrainingLogRecord.training_date,
                ExerciseLibraryRecord.category).join(TrainingLogRecord, TrainingLogRecord.id == TrainingExerciseEntryRecord.log_id)
                .join(ExerciseLibraryRecord, ExerciseLibraryRecord.id == TrainingExerciseEntryRecord.exercise_id)
                .where(TrainingExerciseEntryRecord.user_id == user_id,
                       TrainingLogRecord.training_date >= period_start,
                       TrainingLogRecord.training_date <= period_end)).all()
            entries = [{"sets": entry.sets, "completion": entry.completion, "training_date": training_date,
                        "muscle_group": category} for entry, training_date, category in rows]
            stats = calculate_muscle_stats(entries, period_start, period_end)
            active_dates = sorted({row["training_date"] for row in entries})
            week_count = len({(day.isocalendar().year, day.isocalendar().week) for day in active_dates})
            observed_days = (active_dates[-1] - active_dates[0]).days + 1 if active_dates else 0
            focus = sorted(set(preference.focus_groups + GOAL_FOCUS.get(preference.goal, [])))
            analysis = identify_weak_parts(stats, observed_days if week_count >= 2 else min(observed_days, 13),
                                           focus, preference.excluded_groups)
            for stat in stats:
                saved = db.scalar(select(MuscleGroupStatRecord).where(MuscleGroupStatRecord.user_id == user_id,
                    MuscleGroupStatRecord.period_start == period_start, MuscleGroupStatRecord.period_end == period_end,
                    MuscleGroupStatRecord.muscle_group == stat["muscle_group"]))
                if saved is None:
                    saved = MuscleGroupStatRecord(user_id=user_id, period_start=period_start, period_end=period_end,
                                                  muscle_group=stat["muscle_group"]); db.add(saved)
                saved.frequency = stat["frequency"]; saved.total_sets = stat["total_sets"]
                saved.coverage_percent = stat["coverage_percent"]
            plan = db.get(WeeklyPlanRecord, (user_id, week_start_for(period_end)))
            training_pref = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
            library = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.id)).all()
            equipment = set(training_pref.equipment if training_pref else [])
            eligible_library = [row for row in library if not equipment or "bodyweight_only" in row.equipment or equipment.intersection(row.equipment)]
            advice_items = []
            for weak in analysis["weak_groups"]:
                advice_data = build_addition(weak["muscle_group"], weak, eligible_library,
                                             plan.plan_data if plan else None)
                record = db.scalar(select(WeakPartAdviceRecord).where(WeakPartAdviceRecord.user_id == user_id,
                    WeakPartAdviceRecord.period_end == period_end,
                    WeakPartAdviceRecord.muscle_group == weak["muscle_group"]))
                if record is None:
                    record = WeakPartAdviceRecord(user_id=user_id, period_start=period_start, period_end=period_end,
                                                  muscle_group=weak["muscle_group"], advice_data=advice_data)
                    db.add(record); db.flush()
                elif record.status == "pending": record.advice_data = advice_data
                advice_items.append({"id": record.id, "status": record.status, **record.advice_data})
            db.commit()
            return {**analysis, "period_start": period_start.isoformat(), "period_end": period_end.isoformat(),
                    "observed_weeks": week_count, "stats": stats, "advice": advice_items,
                    "preferences": _preference_dict(preference)}

    @router.put("/weak-parts/{advice_id}")
    def decide_weak_part(advice_id: int, payload: WeakPartDecisionInput,
                         user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            advice = db.scalar(select(WeakPartAdviceRecord).where(WeakPartAdviceRecord.id == advice_id,
                                                                  WeakPartAdviceRecord.user_id == user_id))
            if advice is None: raise HTTPException(404, "未找到这条薄弱部位建议。")
            if advice.status != "pending": raise HTTPException(409, "这条建议已经处理过了。")
            if payload.decision == "adopted":
                week_start = week_start_for(date.today())
                plan = db.get(WeeklyPlanRecord, (user_id, week_start))
                if plan is None: raise HTTPException(409, "请先生成本周训练计划，再采纳加练建议。")
                plan_data = deepcopy(plan.plan_data)
                sessions = plan_data.get("sessions") if isinstance(plan_data.get("sessions"), list) else []
                target_weekday = advice.advice_data.get("target_weekday")
                target = next((row for row in sessions if row.get("weekday") == target_weekday), None)
                if target is None: target = next((row for row in sessions if row.get("focus") == "力量练习"), None)
                if target is None: raise HTTPException(409, "本周计划里没有可加入专项动作的力量训练日。")
                existing_ids = {row.get("id") for row in target.setdefault("exercises", [])}
                additions = []
                for item in advice.advice_data.get("exercises", []):
                    if item.get("id") not in existing_ids:
                        addition = {**item, "sets": 2, "reps_range": "10–15" if item.get("category") == "核心" else "8–12",
                                    "source": "weak_part_advice"}
                        target["exercises"].append(addition); additions.append(addition)
                plan_data.setdefault("special_additions", []).append({"advice_id": advice.id,
                    "muscle_group": advice.muscle_group, "weekday": target.get("weekday"), "exercises": additions})
                plan.plan_data = plan_data
            advice.status = payload.decision; advice.resolved_at = datetime.now(timezone.utc); db.commit()
        return {"ok": True, "status": payload.decision,
                "message": "加练建议已写入本周计划。" if payload.decision == "adopted" else "已忽略本次加练建议，原计划未改变。"}

    @router.delete("/weak-parts/{advice_id}/decision")
    def reset_weak_part_decision(advice_id: int, user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            advice = db.scalar(select(WeakPartAdviceRecord).where(WeakPartAdviceRecord.id == advice_id,
                                                                  WeakPartAdviceRecord.user_id == user_id))
            if advice is None: raise HTTPException(404, "未找到这条薄弱部位建议。")
            if advice.status == "adopted":
                week_start = week_start_for(date.today())
                plan = db.get(WeeklyPlanRecord, (user_id, week_start))
                if plan is not None:
                    plan_data = deepcopy(plan.plan_data)
                    additions = plan_data.get("special_additions") if isinstance(plan_data.get("special_additions"), list) else []
                    applied = next((row for row in additions if row.get("advice_id") == advice.id), None)
                    if applied:
                        applied_ids = {row.get("id") for row in applied.get("exercises", [])}
                        target = next((row for row in plan_data.get("sessions", []) if row.get("weekday") == applied.get("weekday")), None)
                        if target is not None:
                            target["exercises"] = [row for row in target.get("exercises", [])
                                                   if not (row.get("source") == "weak_part_advice" and row.get("id") in applied_ids)]
                        plan_data["special_additions"] = [row for row in additions if row.get("advice_id") != advice.id]
                        plan.plan_data = plan_data
            advice.status = "pending"
            advice.resolved_at = None
            db.commit()
        return {"ok": True, "status": "pending", "message": "已撤销本次处理；由该建议加入的本周专项动作也已移除。"}

    @router.post("/qa")
    def coach_qa(payload: CoachQuestionInput, user_id: int = Depends(authenticate)) -> dict:
        question = payload.question.strip()
        with SessionLocal() as db:
            exercises = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.id)).all()
            plan = db.get(WeeklyPlanRecord, (user_id, week_start_for(date.today())))
            knowledge_rows = db.scalars(select(ExerciseKnowledgeDocumentRecord).where(
                ExerciseKnowledgeDocumentRecord.review_status == "approved")).all()
            retrieved_documents, retrieval_note = ([], None)
            if route_question(question) != "medical":
                retrieved_documents, retrieval_note = retrieve_documents(
                    question, knowledge_rows, allow_semantic=payload.privacy_consent, top_k=8)
            result = answer_coach_question(question, exercises, plan.plan_data if plan else None,
                retrieved_documents=retrieved_documents, retrieval_note=retrieval_note,
                allow_llm=payload.privacy_consent)
            answer = result["answer"]
            db.add(QaLogRecord(user_id=user_id, question=question, answer=answer["answer"],
                intent=result["intent"], exercise_ids=answer["referenced_exercise_ids"], used_llm=result["used_llm"]))
            db.commit()
            matches = {row.id: row for row in result["matches"]}
            references = [_exercise_reference(matches[item]) for item in answer["referenced_exercise_ids"] if item in matches]
            knowledge_sources = [{
                "document_key": row["document_key"], "title": row["title"], "source_name": row["source_name"],
                "source_url": row["source_url"], "source_published_at": row["source_published_at"],
                "retrieved_at": row["source_retrieved_at"], "excerpt": row["body"][:520],
                "retrieval_channels": row["retrieval_channels"], "bm25_score": row["bm25_score"],
                "vector_score": row["vector_score"],
            } for row in result["retrieved_documents"] if row["source_type"] == "external"]
            cited_source_keys = answer.get("referenced_source_keys", [])
        return {"intent": result["intent"], **answer, "used_llm": result["used_llm"], "references": references,
                "knowledge_sources": knowledge_sources, "cited_source_keys": cited_source_keys,
                "embedding_model": EMBEDDING_MODEL,
                "vector_model_used": any("vector" in row["retrieval_channels"] for row in result["retrieved_documents"]),
                "retrieval_method": ("BM25 + 向量 + RRF" if any("vector" in row["retrieval_channels"]
                    for row in result["retrieved_documents"]) else "中文 BM25"),
                "model_note": ("本次已检索动作库，并调用云端通义千问生成回答。" if result["used_llm"]
                              else result.get("fallback_reason", "本次使用本地知识库检索与动作库规则回答。")),
                "retrieval_note": retrieval_note}

    @router.get("/diet-adjustment")
    def get_diet_adjustment(selected_date: date = Query(alias="date"), user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            existing = db.get(DietDayAdjustmentRecord, (user_id, selected_date))
            if existing is not None and existing.status in ("adopted", "ignored"):
                return {"status": existing.status, "date": selected_date.isoformat(), "day_type": existing.day_type,
                        "intensity": existing.intensity, "suggestion": existing.suggestion}
            body = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            profile = db.get(DietProfileRecord, user_id)
            target_result = calculate_targets(body, profile)
            if target_result.get("status") != "ready":
                return {"status": target_result.get("status"), "message": target_result.get("message"),
                        "missing": target_result.get("missing", []), "date": selected_date.isoformat()}
            plan = db.get(WeeklyPlanRecord, (user_id, week_start_for(selected_date)))
            schedule = schedule_for_day(plan.plan_data if plan else None, selected_date)
            training_log = db.scalar(select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id,
                TrainingLogRecord.training_date == selected_date).order_by(TrainingLogRecord.id.desc()).limit(1))
            recovery = db.scalar(select(RecoveryCheckinRecord).where(RecoveryCheckinRecord.user_id == user_id,
                RecoveryCheckinRecord.checkin_date == selected_date).order_by(RecoveryCheckinRecord.id.desc()).limit(1))
            if recovery and recovery.status in ("insufficient", "stop"):
                day_type, intensity = "recovery", "recovery"
            elif schedule.get("status") == "training":
                day_type = "training"
                intensity = "high" if training_log and training_log.rpe and training_log.rpe >= 8 else "regular"
            else:
                day_type, intensity = "rest", "rest"
            suggestion = calculate_day_nutrition(target_result["target"], day_type, intensity)
            if existing is None:
                existing = DietDayAdjustmentRecord(user_id=user_id, adjustment_date=selected_date); db.add(existing)
            existing.day_type = day_type; existing.intensity = intensity; existing.suggestion = suggestion; existing.status = "proposed"
            db.commit()
            return {"status": "proposed", "date": selected_date.isoformat(), "day_type": day_type,
                    "intensity": intensity, "suggestion": suggestion}

    @router.put("/diet-adjustment/{selected_date}")
    def decide_diet_adjustment(selected_date: date, payload: DietAdjustmentDecisionInput,
                               user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            row = db.get(DietDayAdjustmentRecord, (user_id, selected_date))
            if row is None: raise HTTPException(404, "请先生成这一天的饮食联动建议。")
            row.status = payload.decision; db.commit()
        return {"ok": True, "status": payload.decision,
                "message": "已采纳为当天参考目标，基础饮食设置没有改变。" if payload.decision == "adopted" else "已忽略当天联动建议。"}

    @router.get("/reports/auto")
    def get_auto_reports(user_id: int = Depends(authenticate)) -> dict:
        items = []
        with SessionLocal() as db:
            for period_type in ("week", "month"):
                start, end = completed_period(period_type, date.today())
                row = db.scalar(select(ReportSnapshotRecord).where(ReportSnapshotRecord.user_id == user_id,
                    ReportSnapshotRecord.period_type == period_type, ReportSnapshotRecord.period_start == start))
                if row is None:
                    row = ReportSnapshotRecord(user_id=user_id, period_type=period_type, period_start=start,
                        period_end=end, report_data=build_shape_report(db, user_id, period_type, start, end)); db.add(row); db.flush()
                items.append({"id": row.id, "period_type": row.period_type, "period_start": row.period_start.isoformat(),
                    "period_end": row.period_end.isoformat(), "generated_at": row.generated_at.isoformat(), "report": row.report_data})
            db.commit()
        return {"items": items, "trigger": "客户端进入塑型页时补生成最近已完成的周报和月报；同一周期只保存一份快照。"}

    @router.get("/reports")
    def list_reports(period_type: Literal["week", "month"] | None = None,
                     user_id: int = Depends(authenticate)) -> dict:
        with SessionLocal() as db:
            query = select(ReportSnapshotRecord).where(ReportSnapshotRecord.user_id == user_id)
            if period_type: query = query.where(ReportSnapshotRecord.period_type == period_type)
            rows = db.scalars(query.order_by(ReportSnapshotRecord.period_start.desc()).limit(24)).all()
        return {"items": [{"id": row.id, "period_type": row.period_type,
            "period_start": row.period_start.isoformat(), "period_end": row.period_end.isoformat(),
            "generated_at": row.generated_at.isoformat(), "report": row.report_data} for row in rows]}

    return router
