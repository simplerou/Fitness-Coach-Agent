"""HTTP endpoints for plan."""
from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from ..database import (BodyProfileRecord, DEFAULT_TRAINING_WEEKDAYS_BY_COUNT, TrainingPreferencesRecord,
    TrainingSchedulePreferencesRecord, WeeklyPlanRecord)
from ..models.training_intelligence import ExerciseLibraryRecord
from ..schemas.plan import PlanRequest
from ..services.plan_service import week_start_for, serialize_plan_preferences
from ..services.profile_service import get_registration_date
from ..services.training_plan_agent import (TrainingPlanConfigurationError,
    TrainingPlanGenerationError, generate_training_plan)


def create_plan_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.get("/api/plan/current")
    def current_week_plan(user_id: int = Depends(authenticated_user_id)) -> dict:
        week_start = week_start_for(date.today())
        with SessionLocal() as db:
            record = db.scalar(select(WeeklyPlanRecord).where(WeeklyPlanRecord.user_id == user_id, WeeklyPlanRecord.week_start == week_start))
            if record is None:
                return {"week_plan": None, "week_start": week_start.isoformat(), "saved_at": None}
            plan = record.plan_data
            saved_at = record.updated_at.isoformat()
        return {"week_plan": plan, "week_start": week_start.isoformat(), "saved_at": saved_at}

    @router.get("/api/plan/history")
    def plan_history(
        limit: int = Query(default=20, ge=1, le=50),
        before_week_start: date | None = None,
        user_id: int = Depends(authenticated_user_id),
    ) -> dict:
        if before_week_start is not None and before_week_start.weekday() != 0:
            raise HTTPException(status_code=422, detail="分页日期必须是周一。")

        current_week_start = week_start_for(date.today())
        with SessionLocal() as db:
            registration_date = get_registration_date(db, user_id)
            registration_week_start = week_start_for(registration_date)
            query = select(WeeklyPlanRecord).where(
                WeeklyPlanRecord.user_id == user_id, WeeklyPlanRecord.week_start >= registration_week_start
            )
            if before_week_start is not None:
                query = query.where(WeeklyPlanRecord.week_start < before_week_start)
            query = query.order_by(WeeklyPlanRecord.week_start.desc()).limit(limit + 1)
            records = list(db.scalars(query).all())

        has_more = len(records) > limit
        page_records = records[:limit]
        items = [
            {
                "week_start": record.week_start.isoformat(),
                "week_end": (record.week_start + timedelta(days=6)).isoformat(),
                "saved_at": record.updated_at.isoformat(),
                "week_plan": record.plan_data,
            }
            for record in page_records
        ]
        next_before_week_start = (
            page_records[-1].week_start.isoformat()
            if has_more and page_records
            else None
        )
        return {
            "items": items,
            "next_before_week_start": next_before_week_start,
            "registration_date": registration_date.isoformat(),
            "current_week_start": current_week_start.isoformat(),
        }

    @router.get("/api/plan/preferences")
    def get_plan_preferences(user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            record = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
            schedule = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
            if record is None or schedule is None:
                raise HTTPException(status_code=503, detail="本地训练偏好缺失，请重启服务初始化数据库后重试。")
            preferences = serialize_plan_preferences(record, schedule)
            updated_at = record.updated_at.isoformat()
        return {"preferences": preferences, "updated_at": updated_at}

    @router.post("/api/plan")
    def create_plan(payload: PlanRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            body_profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            requested = db.scalars(select(ExerciseLibraryRecord).where(ExerciseLibraryRecord.id.in_(payload.preferred_exercise_ids))).all() if payload.preferred_exercise_ids else []
            if len(requested) != len(payload.preferred_exercise_ids):
                raise HTTPException(status_code=422, detail="选择的训练动作中包含无效动作。")
            incompatible = [item.name for item in requested if not set(item.equipment).intersection(payload.equipment)]
            if incompatible:
                raise HTTPException(status_code=422, detail=f"所选器械不支持这些偏好动作：{'、'.join(incompatible)}。请调整器械或动作。")
            if not requested:
                candidates = db.scalars(select(ExerciseLibraryRecord).order_by(ExerciseLibraryRecord.id)).all()
                requested = [item for item in candidates if any(equipment in payload.equipment for equipment in item.equipment)][:6]
        if body_profile is None:
            raise HTTPException(status_code=409, detail="请先填写个人身体档案，再生成计划。")
        if body_profile.age_band == "under_18":
            raise HTTPException(status_code=422, detail="当前演示版不为未满 18 岁用户自动生成训练计划，请由监护人陪同咨询专业人士。")
        age_guidance = {
            "18_29": "按当前状态和训练经验选择舒适强度，不因年龄自动增加训练量。",
            "30_44": "按当前状态和训练经验选择舒适强度，不因年龄自动增加训练量。",
            "45_59": "优先选择熟悉、无痛的动作，充分热身并为恢复留出时间。",
            "60_plus": "选择可以轻松交谈的强度，按需要延长休息；不适时停止训练。",
        }[body_profile.age_band]
        focus = {
            "strength": "力量基础",
            "fitness": "综合体能",
            "fat_loss": "可持续活动",
        }[payload.goal]
        experience_guidance = {
            "beginner": "选择熟悉、简单且无痛的动作，注重动作控制并留足休息。",
            "some_experience": "优先选择已经掌握且感觉稳定的动作。",
            "experienced": "沿用自己熟悉且无痛的动作，不因经验等级自动增加训练负荷。",
        }[payload.experience_level]
        equipment_labels = {
            "bodyweight_only": "仅自重",
            "dumbbells": "哑铃",
            "resistance_bands": "弹力带",
            "gym": "健身房常见器械",
        }
        selected_equipment = "、".join(equipment_labels[item] for item in payload.equipment)
        equipment_guidance = (
            "仅使用自重完成适合自己的练习。"
            if payload.equipment == ["bodyweight_only"]
            else f"可从已选择的{selected_equipment}中使用自己熟悉的器械。"
        )
        duration_guidance = {
            20: "时间预算约 20 分钟，优先保留简短热身并聚焦主要内容；仍为休息和缓和留出时间。",
            30: "时间预算约 30 分钟，按自己的节奏安排内容，并为热身、休息和缓和留出时间。",
            45: "时间预算约 45 分钟，按自己的节奏安排内容，并为热身、休息和缓和留出时间。",
            60: "时间预算约 60 分钟，按自己的节奏安排内容，并为热身、休息和缓和留出时间。",
        }[payload.session_minutes]

        training_weekdays = sorted(
            payload.training_weekdays
            if payload.training_weekdays is not None
            else DEFAULT_TRAINING_WEEKDAYS_BY_COUNT[payload.days_per_week]
        )
        rest_weekdays = [day for day in range(1, 8) if day not in training_weekdays]
        weekday_labels = {1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六", 7: "周日"}

        candidate_exercises = [{
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "target_muscles": item.target_muscles,
            "equipment": item.equipment,
        } for item in requested]
        try:
            generated_sessions = generate_training_plan({
                "goal": focus,
                "training_weekdays": training_weekdays,
                "training_day_labels": {str(day): weekday_labels[day] for day in training_weekdays},
                "experience_level": payload.experience_level,
                "experience_guidance": experience_guidance,
                "age_related_safety_guidance": age_guidance,
                "equipment": selected_equipment,
                "equipment_guidance": equipment_guidance,
                "session_minutes": payload.session_minutes,
                "duration_guidance": duration_guidance,
                "candidate_exercises": candidate_exercises,
            })
        except TrainingPlanConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TrainingPlanGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        exercise_by_id = {item.id: item for item in requested}
        sessions = []
        for generated in sorted(generated_sessions, key=lambda item: item["weekday"]):
            weekday = generated["weekday"]
            session_exercises = [exercise_by_id[exercise_id] for exercise_id in generated["exercise_ids"]]
            sessions.append({
                "day": weekday_labels[weekday],
                "weekday": weekday,
                "title": generated["title"],
                "focus": generated["focus"],
                "duration_minutes": payload.session_minutes,
                "description": generated["description"],
                "exercises": [{"id": item.id, "name": item.name, "category": item.category,
                    "target_muscles": item.target_muscles} for item in session_exercises],
            })

        plan = {
            "goal": payload.goal,
            "focus": focus,
            "days_per_week": payload.days_per_week,
            "training_weekdays": training_weekdays,
            "rest_weekdays": rest_weekdays,
            "experience_level": payload.experience_level,
            "equipment": payload.equipment,
            "session_minutes": payload.session_minutes,
            "sessions": sessions,
            # 计划快照只保留所用档案时间及选填字段是否存在，不复制身体测量值。
            "body_profile_context": {
                "personal_profile_used": True,
                "height_cm": body_profile.height_cm,
                "weight_kg": body_profile.weight_kg,
                "target_weight_kg": body_profile.target_weight_kg,
            },
            "notice": "这是用于验证流程的通用示例，不是医疗或个体化处方。请结合自身能力及专业人士意见调整。",
        }
        week_start = week_start_for(date.today())
        with SessionLocal() as db:
            preferences = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
            schedule_preferences = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
            if preferences is None or schedule_preferences is None:
                raise HTTPException(status_code=503, detail="本地训练偏好缺失，请重启服务初始化数据库后重试。")
            preferences.goal = payload.goal
            preferences.days_per_week = len(training_weekdays)
            schedule_preferences.weekdays = training_weekdays
            preferences.experience_level = payload.experience_level
            preferences.equipment = payload.equipment
            preferences.session_minutes = payload.session_minutes
            preferences.preferred_exercise_ids = payload.preferred_exercise_ids

            record = db.scalar(select(WeeklyPlanRecord).where(WeeklyPlanRecord.user_id == user_id, WeeklyPlanRecord.week_start == week_start))
            if record is None:
                record = WeeklyPlanRecord(user_id=user_id, week_start=week_start, plan_data=plan)
                db.add(record)
            else:
                record.plan_data = plan
            # 偏好和计划使用同一事务提交，避免仅保存其中一项。
            db.commit()
            db.refresh(record)
            saved_at = record.updated_at.isoformat()
        return {
            "week_plan": plan,
            "week_start": week_start.isoformat(),
            "saved_at": saved_at,
            "message": "千问已根据训练偏好生成计划，本周计划和训练偏好已保存到本机 PostgreSQL。",
            "explanations": [
                "已读取年龄段及身体测量档案：年龄段用于恢复提示，身高体重及选填指标用于后续变化对照；不单独据此判断体能或自动加量。",
                f"已调用项目配置的通义千问模型，根据“{focus}”、每周 {payload.days_per_week} 天、可用器械：{selected_equipment}、训练日：{'、'.join(weekday_labels[day] for day in training_weekdays)}及单次时长约 {payload.session_minutes} 分钟编排训练日内容；动作仅从动作库候选中选择。"
            ],
        }

    return router
