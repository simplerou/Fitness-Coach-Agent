"""HTTP endpoints for diet."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from ..database import (BodyProfileRecord, DailyWaterRecord, DietDayReviewRecord,
    DietMealRecord, DietProfileRecord, LocalProfileRecord)
from ..schemas.diet import DietMealRequest, DietProfileRequest, WaterIntakeRequest
from ..services.boohee_food_service import BooheeFoodServiceError, get_food_detail, search_foods
from ..services.diet_targets import calculate_diet_targets
from ..services.profile_service import get_registration_date


def validate_diet_date(db, user_id: int, selected_day: date) -> None:
    if selected_day < get_registration_date(db, user_id):
        raise HTTPException(status_code=422, detail="所选日期早于账号注册日期，无法记录饮食。")
    if selected_day > date.today():
        raise HTTPException(status_code=422, detail="暂时不能为未来日期记录饮食。")


def apply_diet_meal_values(meal: DietMealRecord, payload: DietMealRequest) -> None:
    meal.log_date = payload.log_date
    meal.meal_type = payload.meal_type
    meal.description = payload.description
    meal.note = payload.note
    meal.portion = payload.portion
    meal.eaten_at = payload.eaten_at
    meal.calories_kcal = payload.calories_kcal
    meal.protein_g = payload.protein_g
    meal.carbs_g = payload.carbs_g
    meal.fat_g = payload.fat_g
    meal.nutrition_source = payload.nutrition_source


def diet_meal_response(meal: DietMealRecord) -> dict:
    return {
        "id": meal.id, "log_date": meal.log_date.isoformat(), "meal_type": meal.meal_type,
        "description": meal.description, "note": meal.note, "portion": meal.portion,
        "eaten_at": meal.eaten_at, "calories_kcal": meal.calories_kcal,
        "protein_g": meal.protein_g, "carbs_g": meal.carbs_g, "fat_g": meal.fat_g,
        "nutrition_source": meal.nutrition_source,
    }


def reset_diet_day_review(db, user_id: int, log_date: date) -> None:
    review = db.get(DietDayReviewRecord, (user_id, log_date))
    if review is not None and review.complete:
        review.complete = False


def create_diet_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.get("/api/diet/foods/search")
    def search_diet_foods(keyword: str = Query(min_length=1, max_length=80), user_id: int = Depends(authenticated_user_id)) -> dict:
        """通过后端代理搜索薄荷食物库，避免 API Key 暴露到浏览器。"""
        del user_id  # 此接口要求登录，但不需要读取或保存用户身份数据。
        try:
            items = search_foods(keyword.strip())
        except BooheeFoodServiceError as exc:
            status_code = 503 if "尚未配置" in str(exc) else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        return {"items": items, "source": "boohee"}

    @router.get("/api/diet/foods/detail")
    def get_diet_food_detail(code: str = Query(min_length=1, max_length=120), user_id: int = Depends(authenticated_user_id)) -> dict:
        """通过薄荷食物 code 查询营养详情，API Key 仍只保留在后端。"""
        del user_id
        try:
            food = get_food_detail(code.strip())
        except BooheeFoodServiceError as exc:
            status_code = 503 if "尚未配置" in str(exc) else 502
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        return {"food": food, "source": "boohee"}

    @router.get("/api/diet/profile")
    def get_diet_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            profile = db.get(DietProfileRecord, user_id)
        if profile is None:
            return {"profile": None}
        fields = (
            "goal", "activity_level", "training_type", "training_time", "training_end_time", "dietary_preference",
            "allergies", "allergies_reviewed", "avoid_foods", "medical_conditions", "injuries", "health_reviewed",
            "cooking_access", "eating_out_per_week", "budget_note", "water_target_ml",
        )
        return {"profile": {field: getattr(profile, field) for field in fields}}

    @router.get("/api/diet/targets")
    def get_diet_targets(user_id: int = Depends(authenticated_user_id)) -> dict:
        """按当前身体与饮食档案返回目标起点，不创建饮食计划快照。"""
        with SessionLocal() as db:
            body = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
            profile = db.get(DietProfileRecord, user_id)
        result = calculate_diet_targets(body, profile)
        result.pop("calculation", None)
        target_ml = profile.water_target_ml if profile else None
        has_health_constraints = bool(profile and ((profile.medical_conditions or "").strip() or (profile.injuries or "").strip()))
        suggested_ml = None
        if body and body.age_years is not None and body.age_years >= 18 and not has_health_constraints:
            suggested_ml = int(body.weight_kg * 0.3 + 0.5) * 100
        result["hydration"] = {
            "target_ml": target_ml,
            "suggested_ml": suggested_ml,
            "source": "user_set" if target_ml is not None else "not_set",
            "basis": "粗略起点：当前体重 × 30 毫升/公斤，按 100 毫升取整；训练安排仅用于提醒饮水时机，不自动增加固定水量。" if suggested_ml is not None else None,
            "note": "这是你设置的日常饮水参考值，不是医疗建议；训练、天气和健康情况可能影响个人需要。" if target_ml is not None else "尚未设置饮水参考值；可以只记录实际饮水，不作目标比较。",
        }
        return result

    @router.put("/api/diet/profile")
    def save_diet_profile(payload: DietProfileRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            profile = db.get(DietProfileRecord, user_id)
            values = payload.model_dump()
            if profile is None:
                profile = DietProfileRecord(user_id=user_id, **values)
                db.add(profile)
            else:
                for field, value in values.items():
                    setattr(profile, field, value)
            db.commit()
        return {"ok": True, "message": "饮食规划档案已保存。"}

    @router.put("/api/diet/day-review")
    def save_diet_day_review(
        log_date: date,
        complete: bool,
        user_id: int = Depends(authenticated_user_id),
    ) -> dict:
        with SessionLocal() as db:
            validate_diet_date(db, user_id, log_date)
            review = db.get(DietDayReviewRecord, (user_id, log_date))
            if review is None:
                review = DietDayReviewRecord(user_id=user_id, log_date=log_date, complete=complete)
                db.add(review)
            else:
                review.complete = complete
            db.commit()
        return {"ok": True, "complete": complete, "message": "当天记录完整度已更新。"}

    @router.get("/api/diet")
    def get_diet_log(log_date: date | None = None, user_id: int = Depends(authenticated_user_id)) -> dict:
        selected_day = log_date or date.today()
        with SessionLocal() as db:
            validate_diet_date(db, user_id, selected_day)
            meals = db.scalars(select(DietMealRecord).where(
                DietMealRecord.user_id == user_id, DietMealRecord.log_date == selected_day,
            ).order_by(DietMealRecord.created_at, DietMealRecord.id)).all()
            water = db.get(DailyWaterRecord, (user_id, selected_day))
            review = db.get(DietDayReviewRecord, (user_id, selected_day))
            items = [{
                "id": meal.id, "meal_type": meal.meal_type, "description": meal.description,
                "note": meal.note, "portion": meal.portion, "eaten_at": meal.eaten_at,
                "calories_kcal": meal.calories_kcal, "protein_g": meal.protein_g,
                "carbs_g": meal.carbs_g, "fat_g": meal.fat_g,
                "nutrition_source": meal.nutrition_source,
                "created_at": meal.created_at.isoformat() if meal.created_at else None,
            } for meal in meals]
            water_ml = water.amount_ml if water else 0
            day_complete = review.complete if review else False
        return {"log_date": selected_day.isoformat(), "items": items, "water_ml": water_ml, "day_complete": day_complete}

    @router.post("/api/diet/meal")
    def create_diet_meal(payload: DietMealRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            validate_diet_date(db, user_id, payload.log_date)
            duplicates = []
            if payload.meal_type != "snack":
                duplicates = db.scalars(select(DietMealRecord).where(
                    DietMealRecord.user_id == user_id,
                    DietMealRecord.log_date == payload.log_date,
                    DietMealRecord.meal_type == payload.meal_type,
                ).order_by(DietMealRecord.id.desc())).all()
            if duplicates:
                meal = duplicates[0]
                for duplicate in duplicates[1:]:
                    db.delete(duplicate)
                apply_diet_meal_values(meal, payload)
                meal_label = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}[payload.meal_type]
                message = f"已有{meal_label}记录，已覆盖更新。"
            else:
                meal = DietMealRecord(user_id=user_id)
                apply_diet_meal_values(meal, payload)
                db.add(meal)
                message = "餐食记录已保存。"
            reset_diet_day_review(db, user_id, payload.log_date)
            db.commit()
            db.refresh(meal)
            result = diet_meal_response(meal)
        return {"ok": True, "meal": result, "message": message}

    @router.put("/api/diet/meal/{meal_id}")
    def update_diet_meal(meal_id: int, payload: DietMealRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            validate_diet_date(db, user_id, payload.log_date)
            meal = db.scalar(select(DietMealRecord).where(
                DietMealRecord.id == meal_id, DietMealRecord.user_id == user_id,
            ))
            if meal is None:
                raise HTTPException(status_code=404, detail="未找到这条餐食记录。")
            previous_date = meal.log_date
            collisions = []
            if payload.meal_type != "snack":
                collisions = db.scalars(select(DietMealRecord).where(
                    DietMealRecord.user_id == user_id,
                    DietMealRecord.log_date == payload.log_date,
                    DietMealRecord.meal_type == payload.meal_type,
                    DietMealRecord.id != meal.id,
                ).order_by(DietMealRecord.id.desc())).all()
            if collisions:
                canonical = collisions[0]
                db.delete(meal)
                for duplicate in collisions[1:]:
                    db.delete(duplicate)
                meal = canonical
            apply_diet_meal_values(meal, payload)
            reset_diet_day_review(db, user_id, previous_date)
            reset_diet_day_review(db, user_id, payload.log_date)
            db.commit()
            db.refresh(meal)
            result = diet_meal_response(meal)
        return {"ok": True, "meal": result, "message": "餐食内容已更新。" }

    @router.delete("/api/diet/meal/{meal_id}")
    def delete_diet_meal(meal_id: int, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            meal = db.scalar(select(DietMealRecord).where(DietMealRecord.id == meal_id, DietMealRecord.user_id == user_id))
            if meal is None:
                raise HTTPException(status_code=404, detail="未找到这条餐食记录。")
            review = db.get(DietDayReviewRecord, (user_id, meal.log_date))
            if review is not None and review.complete:
                review.complete = False
            db.delete(meal)
            db.commit()
        return {"ok": True, "message": "餐食记录已删除；当天完整性标记已重置。"}

    @router.post("/api/diet/water")
    def add_water_intake(payload: WaterIntakeRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            validate_diet_date(db, user_id, payload.log_date)
            water = db.get(DailyWaterRecord, (user_id, payload.log_date))
            current_amount = water.amount_ml if water else 0
            if current_amount + payload.amount_ml > 10000:
                raise HTTPException(status_code=422, detail="当天累计记录不能超过 10000 毫升，请检查输入。")
            if water is None:
                water = DailyWaterRecord(user_id=user_id, log_date=payload.log_date, amount_ml=payload.amount_ml)
                db.add(water)
            else:
                water.amount_ml += payload.amount_ml
            db.commit()
            total_ml = water.amount_ml
        return {"ok": True, "water_ml": total_ml, "message": "饮水记录已累计。"}

    return router
