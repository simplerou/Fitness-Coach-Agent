"""HTTP endpoints for diet plan."""
from __future__ import annotations

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from ..database import (BodyProfileRecord, BodyWeightHistoryRecord, DailyWaterRecord,
    DietDayReviewRecord, DietMealRecord, DietPlanSnapshotRecord, DietProfileRecord,
    TrainingLogRecord, TrainingPreferencesRecord, TrainingSchedulePreferencesRecord)
from ..schemas.diet import DietPlanGenerationRequest
from ..services.diet_agent import DietAgentConfigurationError, DietAgentGenerationError, generate_diet_advice
from ..services.diet_targets import calculate_diet_targets, DIET_ACTIVITY_LABELS, DIET_GOAL_LABELS
from ..services.profile_service import get_registration_date
from ..services.diet_plan_analysis import build_record_analysis


def create_diet_plan_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.post("/api/diet/plan")
    def get_personal_diet_plan(
        payload: DietPlanGenerationRequest,
        user_id: int = Depends(authenticated_user_id),
    ) -> dict:
        del payload  # 明确要求前端确认 AI 数据发送说明后才允许触发模型调用。
        with SessionLocal() as db:
            body = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            profile = db.get(DietProfileRecord, user_id)
            training = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
            schedule = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
            training_logs = db.scalars(select(TrainingLogRecord).where(
                TrainingLogRecord.user_id == user_id,
                TrainingLogRecord.training_date >= date.today() - timedelta(days=6),
                TrainingLogRecord.training_date <= date.today(),
                TrainingLogRecord.completion.in_(("completed", "partial")),
            )).all()
            today = date.today()
            registration_date = get_registration_date(db, user_id)
            week_ago = max(today - timedelta(days=6), registration_date)
            history_start = max(today - timedelta(days=13), registration_date)
            meals = db.scalars(select(DietMealRecord).where(
                DietMealRecord.user_id == user_id,
                DietMealRecord.log_date >= week_ago,
                DietMealRecord.log_date <= today,
            )).all()
            reviews = db.scalars(select(DietDayReviewRecord).where(
                DietDayReviewRecord.user_id == user_id,
                DietDayReviewRecord.log_date >= week_ago,
                DietDayReviewRecord.log_date <= today,
                DietDayReviewRecord.complete.is_(True),
            )).all()
            water_records = db.scalars(select(DailyWaterRecord).where(
                DailyWaterRecord.user_id == user_id,
                DailyWaterRecord.log_date >= week_ago,
                DailyWaterRecord.log_date <= today,
            )).all()
            weight_records = db.scalars(select(BodyWeightHistoryRecord).where(
                BodyWeightHistoryRecord.user_id == user_id,
                BodyWeightHistoryRecord.recorded_on >= history_start,
                BodyWeightHistoryRecord.recorded_on <= today,
            ).order_by(BodyWeightHistoryRecord.recorded_on)).all()
            previous_snapshot = db.scalar(select(DietPlanSnapshotRecord).where(
                DietPlanSnapshotRecord.user_id == user_id,
            ).order_by(DietPlanSnapshotRecord.created_at.desc(), DietPlanSnapshotRecord.id.desc()).limit(1))

        target_result = calculate_diet_targets(body, profile)
        if target_result["status"] != "ready":
            return target_result
        summary = target_result["summary"]
        target = target_result["target"]
        protein_was_capped = target_result["calculation"]["protein_was_capped"]
        bmi = summary["bmi"]
        bmr = summary["bmr_kcal"]
        bmr_source = summary["bmr_source"]
        tdee = summary["tdee_kcal"]
        tdee_source = summary["tdee_source"]
        goal = profile.goal
        calorie_target = target["calories_kcal"]
        macro_targets = {key: target[key] for key in ("protein_g", "carbs_g", "fat_g")}

        (averages, coverage, meal_distribution, hydration_summary,
         training_day_comparison, training_timing_review, diagnosis, warnings) = build_record_analysis(
            meals, reviews, water_records, training_logs, profile, bmr, calorie_target,
            macro_targets, protein_was_capped,
        )
        shares = [("早餐", 0.25), ("午餐", 0.35), ("晚餐", 0.30), ("加餐", 0.10)]
        meal_plan = [{
            "name": name,
            "calories_kcal": round(calorie_target * share),
            "protein_g": round(macro_targets["protein_g"] * share),
            "carbs_g": round(macro_targets["carbs_g"] * share),
            "fat_g": round(macro_targets["fat_g"] * share),
        } for name, share in shares]
        training_info = {
            "frequency_days_per_week": training.days_per_week if training else None,
            "training_days": schedule.weekdays if schedule else None,
            "training_type": profile.training_type,
            "training_time": profile.training_time,
            "training_end_time": profile.training_end_time,
            "session_minutes": training.session_minutes if training else None,
        }
        weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        planning_days = []
        for day_index in range(7):
            plan_date = today + timedelta(days=day_index)
            scheduled_weekdays = schedule.weekdays if schedule else None
            day_type = "训练日" if scheduled_weekdays is not None and plan_date.isoweekday() in scheduled_weekdays else (
                "休息日" if scheduled_weekdays is not None else "未设置训练安排"
            )
            planning_days.append({
                "day_index": day_index,
                "date": plan_date.isoformat(),
                "weekday": weekday_labels[plan_date.weekday()],
                "day_type": day_type,
            })
        if profile.training_time:
            if training_timing_review["days_last_meal_over_4h_before_training"]:
                diagnosis.append(f"在 {training_timing_review['days_with_meal_time_data']} 个同时有完整饮食和进食时间记录的训练日中，有 {training_timing_review['days_last_meal_over_4h_before_training']} 天记录到训练前超过 4 小时没有进食；这只是记录提示，可结合训练感受调整餐次。")
            else:
                training_period = f"{profile.training_time}–{profile.training_end_time}" if profile.training_end_time else f"开始于 {profile.training_time}（结束时间未填写）"
                diagnosis.append(f"训练时段档案为 {training_period}；记录到 {training_timing_review['days_with_meal_time_data']} 个训练日有进食时间数据。可在训练前约 1–3 小时安排正常一餐，训练后约 1–2 小时按下一餐正常进食；无需强行加餐，并结合个人感受调整。")

        meal_type_labels = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐", "snack": "加餐"}
        previous_plan_data = previous_snapshot.plan_data if previous_snapshot else None
        previous_plan_context = None
        if previous_plan_data:
            previous_plan_context = {
                "generated_on": previous_snapshot.generated_on.isoformat(),
                "change_summary": previous_plan_data.get("ai_advice", {}).get("change_summary"),
                "weekly_plan": [
                    {"weekday": day.get("weekday"), "meals": [
                        {"name": meal.get("name"), "example": meal.get("example")}
                        for meal in day.get("meals", [])
                    ]}
                    for day in previous_plan_data.get("weekly_plan", [])
                ],
            }
        agent_input = {
            "profile": {
                "age_years": body.age_years,
                "biological_sex": body.biological_sex,
                "height_cm": body.height_cm,
                "weight_kg": body.weight_kg,
                "bmi_adult_reference": bmi,
                "goal": DIET_GOAL_LABELS[goal],
                "activity_level": DIET_ACTIVITY_LABELS[profile.activity_level],
                "dietary_preference": profile.dietary_preference,
                "allergies": profile.allergies,
                "avoid_foods": profile.avoid_foods,
                "cooking_access": profile.cooking_access,
                "eating_out_per_week": profile.eating_out_per_week,
                "budget_note": profile.budget_note,
                "water_target_ml": profile.water_target_ml,
                "training": training_info,
            },
            "target": target,
            "planning_days": planning_days,
            "previous_plan": previous_plan_context,
            "record_summary": {
                "coverage": coverage,
                "complete_day_averages": averages,
                "meal_distribution": meal_distribution,
                "hydration": hydration_summary,
                "training_day_comparison": training_day_comparison,
                "training_timing_review": training_timing_review,
            },
            "verified_observations": diagnosis,
            "meal_macro_targets_calculated_by_backend": meal_plan,
            "recent_meals": [
                {
                    "date": meal.log_date.isoformat(),
                    "meal": meal_type_labels.get(meal.meal_type, meal.meal_type),
                    "foods": meal.description,
                    "portion": meal.portion,
                    "eaten_at": meal.eaten_at,
                    "calories_kcal": meal.calories_kcal,
                    "protein_g": meal.protein_g,
                    "carbs_g": meal.carbs_g,
                    "fat_g": meal.fat_g,
                    "nutrition_source": meal.nutrition_source,
                }
                for meal in sorted(meals, key=lambda item: (item.log_date, item.eaten_at or "", item.id or 0))[-28:]
            ],
        }
        try:
            ai_advice = generate_diet_advice(agent_input)
        except DietAgentConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except DietAgentGenerationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        weekly_plan = []
        for planned_day in planning_days:
            day_meals = []
            for meal_target in meal_plan:
                example = next(
                    (item["example"] for item in ai_advice["food_examples"]
                     if item["day_index"] == planned_day["day_index"] and item["meal"] == meal_target["name"]),
                    "",
                )
                day_meals.append({**meal_target, "example": example})
            weekly_plan.append({**planned_day, "meals": day_meals})

        result = {
            "status": "ready",
            "summary": {
                "height_cm": body.height_cm, "weight_kg": body.weight_kg,
                "target_weight_kg": body.target_weight_kg,
                "weight_trend_14d": [{"date": row.recorded_on.isoformat(), "weight_kg": row.weight_kg} for row in weight_records],
                "weight_change_14d": round(weight_records[-1].weight_kg - weight_records[0].weight_kg, 1) if len(weight_records) >= 2 else None,
                "bmi": round(bmi, 1),
                "bmr_kcal": round(bmr), "bmr_source": bmr_source,
                "tdee_kcal": round(tdee), "tdee_source": tdee_source,
                "goal": DIET_GOAL_LABELS[goal], "activity_level": DIET_ACTIVITY_LABELS[profile.activity_level],
                "training": training_info,
            },
            "record_summary": {
                "coverage": coverage, "averages": averages,
                "hydration": {**hydration_summary, "target_ml": profile.water_target_ml},
                "training_day_comparison": training_day_comparison,
                "meal_distribution": meal_distribution,
                "training_timing_review": training_timing_review,
            },
            "diagnosis": diagnosis,
            "ai_advice": ai_advice,
            "change_summary": ai_advice["change_summary"],
            "warnings": warnings,
            "target": target,
            "meal_plan": meal_plan,
            "weekly_plan": weekly_plan,
            "food_examples": ai_advice["food_examples"],
            "execution_context": {
                "cooking_access": profile.cooking_access or "未填写",
                "eating_out_per_week": profile.eating_out_per_week,
                "budget_note": profile.budget_note,
                "dietary_preference": profile.dietary_preference,
            },
            "recorded_habits": {
                "keep": ai_advice["habit_to_keep"],
                "adjust": ai_advice["priority_adjustment"],
            },
            "tracking": {
                "period": ai_advice["tracking_period"],
                "next_data": ai_advice["next_data"],
            },
            "assumptions": [
                "BMI 为成人筛查参考数值，不用于诊断。",
                "BMR/TDEE 是估算或用户提供的测量值，会受个体差异影响；请把目标作为起点而非精确处方。",
                "未提供实测 BMR 时使用 Mifflin–St Jeor：男性 10×体重kg + 6.25×身高cm − 5×年龄 + 5；女性末项为 −161。未提供实测 TDEE 时用 BMR 乘所选活动系数。",
                "每餐目标按早餐 25%、午餐 35%、晚餐 30%、加餐 10% 分配；可按作息调整，总量近似。",
                "周计划中的食物例子不绑定精确营养值；精确营养需通过食物库选择食物并记录分量后计算，且需核对过敏原。",
                "当前未采集微量营养素数据，不判断维生素或矿物质缺口；如有担忧请补充专业评估。",
            ],
        }
        with SessionLocal() as db:
            db.add(DietPlanSnapshotRecord(user_id=user_id, generated_on=date.today(), plan_data=result))
            db.commit()
        return result

    @router.get("/api/diet/plan/history")
    def get_diet_plan_history(limit: int = Query(default=8, ge=1, le=50), user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            records = db.scalars(
                select(DietPlanSnapshotRecord)
                .where(DietPlanSnapshotRecord.user_id == user_id)
                .order_by(DietPlanSnapshotRecord.created_at.desc(), DietPlanSnapshotRecord.id.desc())
                .limit(limit)
            ).all()
            items = [{
                "id": item.id,
                "generated_on": item.generated_on.isoformat(),
                "created_at": item.created_at.isoformat(),
                "plan_data": item.plan_data,
            } for item in records]
        return {"items": items}

    return router
