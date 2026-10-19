# FastAPI 应用入口：定义本机演示版 HTTP 接口，并连接页面与 PostgreSQL。
# 确认通过日期暂存于服务进程内；当日暂停状态、计划、状态和训练日志保存在数据库。
from __future__ import annotations

from contextlib import asynccontextmanager
import os
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from .core.security import hash_password, verify_password
from .services.boohee_food_service import BooheeFoodServiceError, get_food_detail, search_foods

from .database import (
    DEFAULT_TRAINING_WEEKDAYS_BY_COUNT,
    AccountUserRecord,
    DailySignalRecord,
    DietMealRecord,
    DailyWaterRecord,
    DietProfileRecord,
    DietDayReviewRecord,
    DietPlanSnapshotRecord,
    BodyProfileRecord,
    BodyWeightHistoryRecord,
    LocalProfileRecord,
    LocalSafetyStateRecord,
    SessionLocal,
    TrainingLogRecord,
    WeeklyPlanRecord,
    TrainingPreferencesRecord,
    TrainingSchedulePreferencesRecord,
    initialize_database,
    claim_legacy_data_for_first_user,
    initialize_user_defaults,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"
DIET_ACTIVITY_FACTORS = {
    "sedentary": 1.2, "light": 1.375, "moderate": 1.55,
    "active": 1.725, "very_active": 1.9,
}
DIET_ACTIVITY_LABELS = {
    "sedentary": "久坐为主", "light": "轻度活动", "moderate": "中等活动",
    "active": "活动较多", "very_active": "高活动量",
}
DIET_GOAL_LABELS = {
    "fat_loss": "减脂", "muscle_gain": "增肌", "maintain": "维持",
    "body_shape": "塑形", "performance": "提升运动表现",
}

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")
SESSION_SECRET_PATH = PROJECT_ROOT / ".session_secret"
if not SESSION_SECRET_KEY:
    if SESSION_SECRET_PATH.exists():
        SESSION_SECRET_KEY = SESSION_SECRET_PATH.read_text(encoding="utf-8").strip()
    else:
        SESSION_SECRET_KEY = secrets.token_urlsafe(48)
        SESSION_SECRET_PATH.write_text(SESSION_SECRET_KEY, encoding="utf-8")


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Fitness Coach Agent", version="1.9.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="fitness_coach_session",
    max_age=12 * 60 * 60,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "0") == "1",
)

# 安全筛查日期按账号保存在进程内；暂停状态按账号写入数据库。
SCREENING_DATES: dict[int, date] = {}
SYMPTOM_LABELS = {
    "chest_pain": "胸痛或胸闷",
    "fainting": "晕厥或接近晕厥",
    "dizziness": "明显眩晕",
    "severe_joint_pain": "严重关节疼痛",
    "other_discomfort": "其他明显不适",
    "uncertain": "无法判断是否存在上述情况",
}


# 以下 Pydantic 模型负责校验前端提交的数据，并限制可接受的字段取值。
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, min_length=1, max_length=32)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    password: str = Field(min_length=1, max_length=128)

class SafetyCheck(BaseModel):
    completed: bool = False
    no_symptoms: bool = False
    symptoms: list[Literal[
        "chest_pain",
        "fainting",
        "dizziness",
        "severe_joint_pain",
        "other_discomfort",
        "uncertain",
    ]] = Field(default_factory=list)


class SafetyResolution(BaseModel):
    confirmed_recovery: bool = False
    followed_professional_advice: bool = False


class DailySignal(BaseModel):
    readiness: Literal["good", "okay", "poor"]
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    resting_hr: int | None = Field(default=None, ge=25, le=240)


class BodyProfileRequest(BaseModel):
    """校验用户自愿提供的身体档案；选填围度不会阻止保存。"""

    age_band: Literal["under_18", "18_29", "30_44", "45_59", "60_plus"]
    height_cm: float = Field(ge=100, le=230)
    weight_kg: float = Field(ge=25, le=300)
    target_weight_kg: float | None = Field(default=None, ge=25, le=300)
    body_fat_percent: float | None = Field(default=None, ge=3, le=70)
    waist_cm: float | None = Field(default=None, ge=30, le=200)


class BodyWeightRequest(BaseModel):
    weight_kg: float = Field(ge=25, le=300)


class PlanRequest(BaseModel):
    goal: Literal["strength", "fitness", "fat_loss"] = "fitness"
    days_per_week: int = Field(default=3, ge=1, le=6)
    training_weekdays: list[int] | None = None
    experience_level: Literal["beginner", "some_experience", "experienced"] = "beginner"
    equipment: list[Literal["bodyweight_only", "dumbbells", "resistance_bands", "gym"]] = Field(
        default_factory=lambda: ["bodyweight_only"]
    )
    session_minutes: Literal[20, 30, 45, 60] = 30

    @model_validator(mode="after")
    def validate_plan_preferences(self):
        if not self.equipment:
            raise ValueError("请至少选择一种可用器械。")
        if len(set(self.equipment)) != len(self.equipment):
            raise ValueError("器械选项不能重复。")
        if "bodyweight_only" in self.equipment and len(self.equipment) > 1:
            raise ValueError("“仅自重”不能与其他器械同时选择。")
        if self.training_weekdays is not None:
            if not 1 <= len(self.training_weekdays) <= 6:
                raise ValueError("每周必须选择 1 到 6 个训练日。")
            if any(day < 1 or day > 7 for day in self.training_weekdays):
                raise ValueError("训练星期编号必须在 1 到 7 之间。")
            if len(set(self.training_weekdays)) != len(self.training_weekdays):
                raise ValueError("训练星期不能重复。")
            if len(self.training_weekdays) != self.days_per_week:
                raise ValueError("每周训练天数必须与选择的星期数量一致。")
        return self


class DietMealRequest(BaseModel):
    log_date: date = Field(default_factory=date.today)
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    description: str = Field(min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=240)
    portion: str | None = Field(default=None, max_length=120)
    eaten_at: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    calories_kcal: float | None = Field(default=None, ge=0, le=5000)
    protein_g: float | None = Field(default=None, ge=0, le=500)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=500)
    nutrition_source: Literal["label", "estimate"] | None = None

    @model_validator(mode="after")
    def trim_description(self):
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("请填写餐食内容。")
        if self.note is not None:
            self.note = self.note.strip() or None
        if self.portion is not None:
            self.portion = self.portion.strip() or None
        if any(value is not None for value in (self.calories_kcal, self.protein_g, self.carbs_g, self.fat_g)) and self.nutrition_source is None:
            raise ValueError("填写营养数据时，请注明来自包装标签还是估算。")
        return self


class DietProfileRequest(BaseModel):
    age_years: int | None = Field(default=None, ge=13, le=100)
    biological_sex: Literal["female", "male", "unspecified"] | None = None
    muscle_mass_kg: float | None = Field(default=None, ge=10, le=200)
    measured_bmr: float | None = Field(default=None, ge=500, le=6000)
    measured_tdee: float | None = Field(default=None, ge=800, le=10000)
    goal: Literal["fat_loss", "muscle_gain", "maintain", "body_shape", "performance"] | None = None
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"] | None = None
    training_type: Literal["strength", "cardio", "mixed", "other"] | None = None
    training_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    dietary_preference: str | None = Field(default=None, max_length=48)
    allergies: str | None = Field(default=None, max_length=500)
    allergies_reviewed: bool = False
    avoid_foods: str | None = Field(default=None, max_length=500)
    medical_conditions: str | None = Field(default=None, max_length=500)
    injuries: str | None = Field(default=None, max_length=500)
    health_reviewed: bool = False
    cooking_access: Literal["none", "basic", "full"] | None = None
    eating_out_per_week: int | None = Field(default=None, ge=0, le=21)
    budget_note: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_training_time(self):
        if self.training_time:
            try:
                datetime.strptime(self.training_time, "%H:%M")
            except ValueError as exc:
                raise ValueError("训练时间请使用 24 小时制时:分。") from exc
        for field in ("dietary_preference", "allergies", "avoid_foods", "medical_conditions", "injuries", "budget_note"):
            value = getattr(self, field)
            if value is not None:
                cleaned = value.strip() or None
                if field == "medical_conditions" and cleaned and cleaned.lower() in ("无", "没有", "无已知疾病", "none", "no"):
                    cleaned = None
                setattr(self, field, cleaned)
        return self


class WaterIntakeRequest(BaseModel):
    log_date: date = Field(default_factory=date.today)
    amount_ml: int = Field(ge=50, le=3000)


class TrainingLog(BaseModel):
    training_date: date = Field(default_factory=date.today)
    completion: Literal["completed", "partial", "skipped"]
    rpe: int | None = Field(default=None, ge=1, le=10)
    skip_reason: Literal["no_time", "too_tired", "discomfort", "other"] | None = None
    note: str | None = Field(default=None, max_length=240)


# 统一用周一作为一周的键，确保计划保存、查询和历史分页使用同一边界。
def authenticated_user_id(request: Request) -> int:
    """从签名会话读取账号，并确认账号仍存在。"""
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="请先登录后继续。")
    with SessionLocal() as db:
        if db.get(AccountUserRecord, user_id) is None:
            request.session.clear()
            raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录。")
    return user_id

def week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())

# 仅今日训练相关接口检查确认状态；周计划、历史和档案接口保持可访问。
def require_clear_safety_screen(user_id: int, action_date: date | None = None) -> None:
    action_date = action_date or date.today()
    if action_date != date.today():
        return
    with SessionLocal() as db:
        safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
        if safety_state is None:
            raise HTTPException(status_code=503, detail="本地安全状态缺失，请重启服务初始化数据库后重试。")
        if safety_state.hold_active and safety_state.hold_date == action_date:
            raise HTTPException(status_code=423, detail="今天的训练建议已暂停；请休息，并在新的一天重新确认。")
    if SCREENING_DATES.get(user_id) != action_date:
        raise HTTPException(status_code=409, detail="请先在今日页面确认身体状态，再记录今天的训练状态。")

@app.post("/api/auth/register")
def register_account(payload: RegisterRequest, request: Request) -> dict:
    username = payload.username.strip().lower()
    display_name = (payload.display_name or username).strip()
    salt, password_hash_value = hash_password(payload.password)
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(748219036)"))
        existing = db.scalar(select(AccountUserRecord).where(AccountUserRecord.username == username))
        if existing is not None:
            raise HTTPException(status_code=409, detail="这个用户名已被注册，请换一个用户名。")
        account_count = db.scalar(select(func.count(AccountUserRecord.id))) or 0
        user = AccountUserRecord(
            username=username,
            display_name=display_name,
            password_hash=password_hash_value,
            password_salt=salt,
        )
        db.add(user)
        db.flush()
        if account_count == 0:
            claim_legacy_data_for_first_user(db, user.id)
        initialize_user_defaults(db, user.id, date.today())
        db.commit()
        user_id = user.id
    request.session.clear()
    request.session["user_id"] = user_id
    SCREENING_DATES.pop(user_id, None)
    return {"user": {"id": user_id, "username": username, "display_name": display_name}}


@app.post("/api/auth/login")
def login_account(payload: LoginRequest, request: Request) -> dict:
    username = payload.username.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(AccountUserRecord).where(AccountUserRecord.username == username))
        if user is None or not verify_password(payload.password, user.password_salt, user.password_hash):
            # Use the same response for unknown usernames and incorrect passwords.
            verify_password(payload.password, "00" * 24, "00" * 64)
            raise HTTPException(status_code=401, detail="用户名或密码不正确。")
        user_id = user.id
        display_name = user.display_name
    request.session.clear()
    request.session["user_id"] = user_id
    SCREENING_DATES.pop(user_id, None)
    return {"user": {"id": user_id, "username": username, "display_name": display_name}}


@app.get("/api/auth/me")
def current_account(user_id: int = Depends(authenticated_user_id)) -> dict:
    with SessionLocal() as db:
        user = db.get(AccountUserRecord, user_id)
        return {"user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


@app.post("/api/auth/logout")
def logout_account(request: Request, user_id: int = Depends(authenticated_user_id)) -> dict:
    request.session.clear()
    SCREENING_DATES.pop(user_id, None)
    return {"ok": True}

@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "1.9.0", "storage": "postgresql"}


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_, __):
    return JSONResponse(
        status_code=503,
        content={"detail": "数据库暂时不可用。请确认 PostgreSQL 服务正在运行、移动硬盘已连接，然后重试。"},
    )


# 每次服务启动后需要重新确认；命中不适后暂停当日训练建议，次日可重新确认。
@app.post("/api/safety-check")
def safety_check(payload: SafetyCheck, user_id: int = Depends(authenticated_user_id)) -> dict:
    today = date.today()
    SCREENING_DATES.pop(user_id, None)
    with SessionLocal() as db:
        safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
        if safety_state is None:
            raise HTTPException(status_code=503, detail="本地安全状态缺失，请重启服务初始化数据库后重试。")
        if safety_state.hold_active and safety_state.hold_date == today:
            return {
                "status": "stop",
                "screening_date": today.isoformat(),
                "message": "今天的训练建议已暂停，请休息。若出现紧急或严重症状，请及时联系当地急救或医疗服务。",
                "symptoms": [],
            }
        if not payload.completed:
            return {"status": "ask", "message": "请确认今天的身体感受。", "symptoms": []}
        if payload.no_symptoms and payload.symptoms:
            raise HTTPException(status_code=422, detail="不能同时选择“没有不适”和“有不适或无法判断”。")
        if payload.symptoms:
            safety_state.hold_active = True
            safety_state.hold_date = today
            safety_state.hold_requires_professional_confirmation = False
            db.commit()
            labels = [SYMPTOM_LABELS[item] for item in payload.symptoms]
            return {
                "status": "stop",
                "screening_date": today.isoformat(),
                "message": "今天先暂停训练建议并休息。若症状紧急、严重、持续或加重，请及时联系医疗服务。",
                "symptoms": labels,
            }
        if not payload.no_symptoms:
            return {"status": "ask", "message": "请确认今天是否有明显不适。", "symptoms": []}
        safety_state.hold_active = False
        safety_state.hold_date = None
        safety_state.hold_requires_professional_confirmation = False
        db.commit()
    SCREENING_DATES[user_id] = today
    return {
        "status": "clear",
        "screening_date": today.isoformat(),
        "message": "今日身体状态已确认。",
        "symptoms": [],
    }

@app.post("/api/daily-signal")
def save_daily_signal(payload: DailySignal, user_id: int = Depends(authenticated_user_id)) -> dict:
    require_clear_safety_screen(user_id)
    today = date.today()
    with SessionLocal() as db:
        record = db.scalar(select(DailySignalRecord).where(DailySignalRecord.user_id == user_id, DailySignalRecord.signal_date == today))
        if record is None:
            record = DailySignalRecord(user_id=user_id, signal_date=today, **payload.model_dump())
            db.add(record)
        else:
            record.readiness = payload.readiness
            record.sleep_hours = payload.sleep_hours
            record.resting_hr = payload.resting_hr
        db.commit()
    return {
        "accepted": True,
        "source": "manual",
        "recorded_at": today.isoformat(),
        "message": "状态已保存到本机 PostgreSQL 数据库。",
    }


# 当前周计划从数据库读取；没有本周记录时返回空状态，不生成默认计划。
@app.get("/api/plan/current")
def current_week_plan(user_id: int = Depends(authenticated_user_id)) -> dict:
    week_start = week_start_for(date.today())
    with SessionLocal() as db:
        record = db.scalar(select(WeeklyPlanRecord).where(WeeklyPlanRecord.user_id == user_id, WeeklyPlanRecord.week_start == week_start))
        if record is None:
            return {"week_plan": None, "week_start": week_start.isoformat(), "saved_at": None}
        plan = record.plan_data
        saved_at = record.updated_at.isoformat()
    return {"week_plan": plan, "week_start": week_start.isoformat(), "saved_at": saved_at}


# 历史接口只读数据库快照；游标用周一起始日继续向更早记录翻页。
@app.get("/api/plan/history")
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

# 按用户选择的训练条件生成本地模板，并在同一事务保存偏好和本周快照。
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
    }


@app.get("/api/body-profile")
def get_body_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
    """读取当前身体档案和最近体重变化；本机单用户演示不要求先完成筛查。"""
    with SessionLocal() as db:
        profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
        history = db.scalars(
            select(BodyWeightHistoryRecord).where(BodyWeightHistoryRecord.user_id == user_id).order_by(BodyWeightHistoryRecord.recorded_on.desc()).limit(12)
        ).all()
        if profile is None:
            return {"profile": None, "weight_history": []}
        serialized = {
            "age_band": profile.age_band,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "target_weight_kg": profile.target_weight_kg,
            "body_fat_percent": profile.body_fat_percent,
            "waist_cm": profile.waist_cm,
            "updated_at": profile.updated_at.isoformat(),
        }
        weights = [{"date": row.recorded_on.isoformat(), "weight_kg": row.weight_kg} for row in history]
    return {"profile": serialized, "weight_history": weights}


@app.post("/api/body-weight")
def save_body_weight(payload: BodyWeightRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
    """单独记录今日体重，并同步更新当前档案中的体重。"""
    today = date.today()
    with SessionLocal() as db:
        profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
        if profile is None:
            raise HTTPException(status_code=409, detail="请先填写身体档案，再记录体重。")
        record = db.get(BodyWeightHistoryRecord, (user_id, today))
        if record is None:
            db.add(BodyWeightHistoryRecord(user_id=user_id, recorded_on=today, weight_kg=payload.weight_kg))
        else:
            record.weight_kg = payload.weight_kg
        profile.weight_kg = payload.weight_kg
        db.commit()
    return {"ok": True, "recorded_on": today.isoformat(), "weight_kg": payload.weight_kg, "message": "今日体重已记录。"}


@app.put("/api/body-profile")
def save_body_profile(payload: BodyProfileRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
    """保存最新身体档案，并按日期保留体重记录。"""
    with SessionLocal() as db:
        profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
        if profile is None:
            profile = BodyProfileRecord(user_id=user_id, **payload.model_dump())
            db.add(profile)
        else:
            for field, value in payload.model_dump().items():
                setattr(profile, field, value)
        today_weight = db.get(BodyWeightHistoryRecord, (user_id, date.today()))
        if today_weight is None:
            db.add(BodyWeightHistoryRecord(user_id=user_id, recorded_on=date.today(), weight_kg=payload.weight_kg))
        else:
            today_weight.weight_kg = payload.weight_kg
        db.commit()
        db.refresh(profile)
        updated_at = profile.updated_at.isoformat()
    return {"ok": True, "updated_at": updated_at, "message": "个人身体档案已保存；体重变化按日期记录。"}


@app.delete("/api/body-profile")
def delete_body_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
    """删除身体档案及其体重历史，不删除训练计划和其他训练记录。"""
    with SessionLocal() as db:
        profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
        if profile is not None:
            db.delete(profile)
        db.query(BodyWeightHistoryRecord).filter(BodyWeightHistoryRecord.user_id == user_id).delete(synchronize_session=False)
        db.commit()
    return {"ok": True, "message": "个人身体档案和体重历史已删除。"}

@app.get("/api/plan/preferences")
def get_plan_preferences(user_id: int = Depends(authenticated_user_id)) -> dict:
    with SessionLocal() as db:
        record = db.scalar(select(TrainingPreferencesRecord).where(TrainingPreferencesRecord.user_id == user_id))
        schedule = db.scalar(select(TrainingSchedulePreferencesRecord).where(TrainingSchedulePreferencesRecord.user_id == user_id))
        if record is None or schedule is None:
            raise HTTPException(status_code=503, detail="本地训练偏好缺失，请重启服务初始化数据库后重试。")
        preferences = serialize_plan_preferences(record, schedule)
        updated_at = record.updated_at.isoformat()
    return {"preferences": preferences, "updated_at": updated_at}


@app.post("/api/plan")
def create_plan(payload: PlanRequest, user_id: int = Depends(authenticated_user_id)) -> dict:
    with SessionLocal() as db:
        body_profile = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
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

    sessions = []
    for index, weekday in enumerate(training_weekdays):
        if index % 2 == 0:
            title = {"strength": "力量基础练习", "fitness": "全身力量练习", "fat_loss": "日常活动与基础力量"}[payload.goal]
            session_focus = "力量练习"
            description = f"{equipment_guidance}{experience_guidance}{age_guidance}{duration_guidance}"
        else:
            title = "轻松有氧与活动度"
            session_focus = "轻松有氧与活动度"
            description = (
                f"选择可以轻松交谈的活动与活动度练习。{age_guidance}{duration_guidance}"
                "感觉不适时停止。"
            )
        sessions.append({
            "day": weekday_labels[weekday],
            "weekday": weekday,
            "title": title,
            "focus": session_focus,
            "duration_minutes": payload.session_minutes,
            "description": description,
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
        "message": "本周计划和训练偏好已保存到本机 PostgreSQL。",
        "explanations": [
            "已读取年龄段及身体测量档案：年龄段用于恢复提示，身高体重及选填指标用于后续变化对照；不单独据此判断体能或自动加量。",
            f"按“{focus}”、每周 {payload.days_per_week} 天、可用器械：{selected_equipment}，训练日：{'、'.join(weekday_labels[day] for day in training_weekdays)}，单次约 {payload.session_minutes} 分钟，生成本地模板。"
        ],
    }


# 从周计划快照中找出某个日期的安排；旧快照缺少星期时不猜测训练日。
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


# 今日接口返回确认状态；暂停只影响当天安排，不影响周计划或历史查看。
@app.get("/api/today")
def today(user_id: int = Depends(authenticated_user_id)) -> dict:
    selected_day = date.today()
    week_start = week_start_for(selected_day)
    with SessionLocal() as db:
        plan_record = db.scalar(select(WeeklyPlanRecord).where(
            WeeklyPlanRecord.user_id == user_id,
            WeeklyPlanRecord.week_start == week_start,
        ))
        today_schedule = serialize_today_schedule(
            plan_record.plan_data if plan_record is not None else None,
            selected_day,
        )
        if today_schedule["status"] == "rest":
            return {
                "level": "rest_day",
                "screening_date": selected_day.isoformat(),
                "message": "今天是当前周计划中的休息日，无需填写训练状态。",
                "today_schedule": today_schedule,
                "plan_items": [],
                "reasons": ["计划休息日无需提交训练状态"],
            }

        safety_state = db.scalar(select(LocalSafetyStateRecord).where(LocalSafetyStateRecord.user_id == user_id))
        if safety_state is None:
            raise HTTPException(status_code=503, detail="本地安全状态缺失，请重启服务初始化数据库后重试。")
        if safety_state.hold_active and safety_state.hold_date == selected_day:
            return {
                "level": "stop",
                "screening_date": selected_day.isoformat(),
                "message": "今天的训练建议已暂停，请休息。周计划和历史记录仍可查看。",
                "plan_items": [],
                "reasons": ["今天报告有不适或无法判断身体状态"],
            }
        if SCREENING_DATES.get(user_id) != selected_day:
            SCREENING_DATES.pop(user_id, None)
            return {
                "level": "ask",
                "message": "请先在上方小模块确认今天的身体感受。",
                "plan_items": [],
                "reasons": ["完成确认后再显示今天的训练安排"],
            }

        signal_record = db.scalar(select(DailySignalRecord).where(
            DailySignalRecord.user_id == user_id,
            DailySignalRecord.signal_date == selected_day,
        ))
        signal = (
            {
                "readiness": signal_record.readiness,
                "sleep_hours": signal_record.sleep_hours,
                "resting_hr": signal_record.resting_hr,
            }
            if signal_record else None
        )

    if signal is None:
        return {
            "level": "insufficient_data",
            "screening_date": selected_day.isoformat(),
            "message": "还没有记录今天的主观状态，暂时无法判断是否需要调整。",
            "plan_items": [],
            "reasons": ["今日状态数据未提供；缺失不代表状态正常"],
        }
    if signal["readiness"] == "poor":
        return {
            "level": "downgrade",
            "screening_date": selected_day.isoformat(),
            "message": "你报告今天状态较差。考虑降低训练强度或休息；如有疼痛或明显不适，请停止训练并寻求专业帮助。",
            "plan_items": [],
            "reasons": ["依据：用户报告今日状态较差"],
        }

    today_session = today_schedule["session"]
    return {
        "level": "normal",
        "screening_date": selected_day.isoformat(),
        "message": f"你报告今天状态尚可。{today_schedule['message']}",
        "today_schedule": today_schedule,
        "plan_items": [today_session] if today_schedule["status"] == "training" else [],
        "reasons": [f"依据：用户报告今日状态为 {'良好' if signal['readiness'] == 'good' else '一般'}"],
    }

def get_registration_date(db, user_id: int) -> date:
    profile = db.scalar(select(LocalProfileRecord).where(LocalProfileRecord.user_id == user_id))
    return profile.registered_on if profile else date.today()


def validate_diet_date(db, user_id: int, selected_day: date) -> None:
    if selected_day < get_registration_date(db, user_id):
        raise HTTPException(status_code=422, detail="所选日期早于账号注册日期，无法记录饮食。")
    if selected_day > date.today():
        raise HTTPException(status_code=422, detail="暂时不能为未来日期记录饮食。")


def calculate_diet_targets(body, profile) -> dict:
    """按身体档案与饮食档案计算每日营养目标起点；不读取或写入历史计划。"""
    if body is None:
        return {"status": "needs_data", "missing": ["个人身体档案：身高和当前体重"], "message": "先填写身体档案，才能估算个性化营养目标。"}
    if body.age_band == "under_18":
        return {"status": "professional_support", "message": "青少年仍处于生长发育阶段，本工具不生成成人热量或宏量营养素目标；建议和监护人一起咨询医生或注册营养师。"}
    if profile is None:
        return {"status": "needs_data", "missing": ["饮食规划档案"], "message": "请补充饮食规划档案后生成个性化目标。"}

    missing = []
    if profile.age_years is None: missing.append("具体年龄")
    if profile.biological_sex not in ("female", "male"): missing.append("用于代谢公式的生理性别")
    if not profile.goal: missing.append("健身目标")
    if not profile.activity_level: missing.append("日常活动水平")
    if not profile.health_reviewed: missing.append("健康约束确认")
    if not profile.allergies_reviewed: missing.append("过敏源与忌口确认")
    if missing:
        return {"status": "needs_data", "missing": missing, "message": "补充这些信息后，系统才能计算参考目标。"}
    if profile.age_years < 18:
        return {"status": "professional_support", "message": "未满 18 岁不生成成人热量或宏量营养素目标；建议和监护人一起咨询医生或注册营养师。"}

    age_ranges = {"18_29": (18, 29), "30_44": (30, 44), "45_59": (45, 59), "60_plus": (60, 100)}
    age_range = age_ranges.get(body.age_band)
    if age_range and not age_range[0] <= profile.age_years <= age_range[1]:
        return {"status": "data_conflict", "message": "身体档案年龄段与饮食档案中的具体年龄不一致，请先修正后再计算。"}
    if (profile.medical_conditions or "").strip() or (profile.injuries or "").strip():
        return {"status": "professional_support", "message": "档案中记录了疾病、孕期、进食障碍、伤病或其他健康情况。请咨询医生或注册营养师后再设定营养目标。"}

    height_m = body.height_cm / 100
    bmi = body.weight_kg / (height_m * height_m)
    if profile.measured_bmr is not None:
        bmr, bmr_source = profile.measured_bmr, "用户提供的测量值"
    else:
        sex_adjustment = 5 if profile.biological_sex == "male" else -161
        bmr = 10 * body.weight_kg + 6.25 * body.height_cm - 5 * profile.age_years + sex_adjustment
        bmr_source = "Mifflin–St Jeor 公式估算"
    if profile.measured_tdee is not None:
        tdee, tdee_source = profile.measured_tdee, "用户提供的测量值"
    else:
        factor = DIET_ACTIVITY_FACTORS[profile.activity_level]
        tdee = bmr * factor
        tdee_source = f"BMR × 活动系数 {factor}（{DIET_ACTIVITY_LABELS[profile.activity_level]}）"
    if tdee < bmr:
        return {"status": "data_conflict", "message": "TDEE 低于 BMR，请核对测量值与活动水平。"}
    if profile.goal == "fat_loss" and bmi < 18.5:
        return {"status": "professional_support", "message": "成人 BMI 参考值低于 18.5，系统不会生成减脂目标。建议咨询医生或注册营养师。"}

    if profile.goal == "fat_loss":
        calorie_target = max(bmr, tdee * 0.9)
        target_note = "温和约 10% 能量缺口，并确保估算目标不低于 BMR"
    elif profile.goal == "muscle_gain":
        calorie_target = tdee * 1.05
        target_note = "以 TDEE 为基准增加约 5%，属于保守起点"
    else:
        calorie_target = tdee
        target_note = "以估算 TDEE 作为维持基线；塑形不自动等同于减脂"
    protein_raw = 1.6 * body.weight_kg
    protein = min(protein_raw, calorie_target * 0.35 / 4)
    fat = calorie_target * 0.25 / 9
    carbs = max(0, (calorie_target - protein * 4 - fat * 9) / 4)
    calorie_target = round(calorie_target)
    macro_targets = {"protein_g": round(protein), "carbs_g": round(carbs), "fat_g": round(fat)}
    basis = f"{target_note}；蛋白质按约 1.6 克/公斤体重估算（若超过目标能量的 35% 则限制显示）；脂肪约占能量 25%，剩余能量分配给碳水。"
    return {
        "status": "ready",
        "summary": {
            "age_years": profile.age_years, "height_cm": body.height_cm, "weight_kg": body.weight_kg,
            "bmi": round(bmi, 1), "bmr_kcal": round(bmr), "bmr_source": bmr_source,
            "tdee_kcal": round(tdee), "tdee_source": tdee_source,
            "goal": DIET_GOAL_LABELS[profile.goal], "activity_level": DIET_ACTIVITY_LABELS[profile.activity_level],
        },
        "target": {
            "calories_kcal": calorie_target, **macro_targets,
            "protein_percent": round(macro_targets["protein_g"] * 4 / calorie_target * 100),
            "carbs_percent": round(macro_targets["carbs_g"] * 4 / calorie_target * 100),
            "fat_percent": round(macro_targets["fat_g"] * 9 / calorie_target * 100),
            "basis": basis,
        },
        "warnings": (["按体重计算的蛋白质目标超过目标能量的 35%，已限制显示；可咨询注册营养师评估。"] if protein < protein_raw else []),
        "calculation": {"target_note": target_note, "protein_was_capped": protein < protein_raw},
    }


@app.get("/api/diet/foods/search")
def search_diet_foods(keyword: str = Query(min_length=1, max_length=80), user_id: int = Depends(authenticated_user_id)) -> dict:
    """通过后端代理搜索薄荷食物库，避免 API Key 暴露到浏览器。"""
    del user_id  # 此接口要求登录，但不需要读取或保存用户身份数据。
    try:
        items = search_foods(keyword.strip())
    except BooheeFoodServiceError as exc:
        status_code = 503 if "尚未配置" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"items": items, "source": "boohee"}


@app.get("/api/diet/foods/detail")
def get_diet_food_detail(code: str = Query(min_length=1, max_length=120), user_id: int = Depends(authenticated_user_id)) -> dict:
    """通过薄荷食物 code 查询营养详情，API Key 仍只保留在后端。"""
    del user_id
    try:
        food = get_food_detail(code.strip())
    except BooheeFoodServiceError as exc:
        status_code = 503 if "尚未配置" in str(exc) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {"food": food, "source": "boohee"}


@app.get("/api/diet/profile")
def get_diet_profile(user_id: int = Depends(authenticated_user_id)) -> dict:
    with SessionLocal() as db:
        profile = db.get(DietProfileRecord, user_id)
    if profile is None:
        return {"profile": None}
    fields = (
        "age_years", "biological_sex", "muscle_mass_kg", "measured_bmr", "measured_tdee",
        "goal", "activity_level", "training_type", "training_time", "dietary_preference",
        "allergies", "allergies_reviewed", "avoid_foods", "medical_conditions", "injuries", "health_reviewed",
        "cooking_access", "eating_out_per_week", "budget_note",
    )
    return {"profile": {field: getattr(profile, field) for field in fields}}


@app.get("/api/diet/targets")
def get_diet_targets(user_id: int = Depends(authenticated_user_id)) -> dict:
    """按当前身体与饮食档案返回目标起点，不创建饮食计划快照。"""
    with SessionLocal() as db:
        body = db.scalar(select(BodyProfileRecord).where(BodyProfileRecord.user_id == user_id))
        profile = db.get(DietProfileRecord, user_id)
    result = calculate_diet_targets(body, profile)
    result.pop("calculation", None)
    return result


@app.put("/api/diet/profile")
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


@app.put("/api/diet/day-review")
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


@app.get("/api/diet")
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


@app.post("/api/diet/meal")
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


@app.put("/api/diet/meal/{meal_id}")
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

@app.get("/api/diet/plan")
def get_personal_diet_plan(user_id: int = Depends(authenticated_user_id)) -> dict:
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

    complete_dates = {row.log_date for row in reviews}
    by_day = {}
    discrepancies = []
    for meal in meals:
        day = by_day.setdefault(meal.log_date, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0,
                                                "kcal_complete": True, "protein_complete": True,
                                                "carbs_complete": True, "fat_complete": True, "count": 0})
        day["count"] += 1
        macros_complete = all(value is not None for value in (meal.protein_g, meal.carbs_g, meal.fat_g))
        derived_kcal = (meal.protein_g * 4 + meal.carbs_g * 4 + meal.fat_g * 9) if macros_complete else None
        kcal = meal.calories_kcal if meal.calories_kcal is not None else derived_kcal
        if kcal is None: day["kcal_complete"] = False
        else: day["calories"] += kcal
        for key, value in (("protein", meal.protein_g), ("carbs", meal.carbs_g), ("fat", meal.fat_g)):
            if value is None: day[key + "_complete"] = False
            else: day[key] += value
        if meal.calories_kcal is not None and derived_kcal is not None and max(meal.calories_kcal, derived_kcal) > 0:
            if abs(meal.calories_kcal - derived_kcal) / max(meal.calories_kcal, derived_kcal) > 0.25:
                discrepancies.append(meal.log_date.isoformat())
    tracked_days = [by_day[d] for d in complete_dates if d in by_day]
    averages = {}
    metric_day_counts = {}
    for key, complete_key in (
        ("calories", "kcal_complete"), ("protein", "protein_complete"),
        ("carbs", "carbs_complete"), ("fat", "fat_complete"),
    ):
        values = [day[key] for day in tracked_days if day[complete_key]]
        metric_day_counts[key] = len(values)
        averages[key] = round(sum(values) / len(values)) if len(values) >= 3 else None
    actual_training_dates = {record.training_date for record in training_logs}
    training_values = [by_day[d]["carbs"] for d in complete_dates
                       if d in by_day and d in actual_training_dates and by_day[d]["carbs_complete"]]
    rest_values = [by_day[d]["carbs"] for d in complete_dates
                   if d in by_day and d not in actual_training_dates and by_day[d]["carbs_complete"]]
    training_day_comparison = {
        "training_days_with_data": len(training_values),
        "rest_days_with_data": len(rest_values),
        "training_day_carbs_g": round(sum(training_values) / len(training_values)) if training_values else None,
        "rest_day_carbs_g": round(sum(rest_values) / len(rest_values)) if rest_values else None,
    }
    meal_counts = {label: sum(1 for meal in meals if meal.meal_type == key)
                   for key, label in (("breakfast", "早餐"), ("lunch", "午餐"), ("dinner", "晚餐"), ("snack", "加餐"))}
    meal_description_counts = {}
    for meal in meals:
        normalized = " ".join(meal.description.split())
        if normalized:
            meal_description_counts[normalized] = meal_description_counts.get(normalized, 0) + 1
    common_meals = [
        {"description": label, "count": count}
        for label, count in sorted(meal_description_counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ][:3]
    meal_distribution = {
        "counts": meal_counts,
        "timed_meals": sum(1 for meal in meals if meal.eaten_at),
        "meals_with_portion": sum(1 for meal in meals if meal.portion),
        "repeated_meals": common_meals,
    }
    training_timing_review = {"training_days_with_complete_logs": 0, "days_with_meal_time_data": 0,
                              "days_last_meal_over_4h_before_training": 0}
    if profile.training_time:
        training_minute = int(profile.training_time[:2]) * 60 + int(profile.training_time[3:])
        for day_date in complete_dates.intersection(actual_training_dates):
            day_meals = [meal for meal in meals if meal.log_date == day_date and meal.eaten_at]
            if not day_meals:
                continue
            training_timing_review["training_days_with_complete_logs"] += 1
            training_timing_review["days_with_meal_time_data"] += 1
            meal_minutes = [int(meal.eaten_at[:2]) * 60 + int(meal.eaten_at[3:]) for meal in day_meals]
            earlier_meals = [minute for minute in meal_minutes if minute <= training_minute]
            if earlier_meals and training_minute - max(earlier_meals) > 240:
                training_timing_review["days_last_meal_over_4h_before_training"] += 1

    water_by_day = {record.log_date: record.amount_ml for record in water_records}
    hydration_summary = {
        "days_logged": len(water_by_day),
        "total_ml": sum(water_by_day.values()) if water_by_day else None,
        "average_on_logged_days_ml": round(sum(water_by_day.values()) / len(water_by_day)) if water_by_day else None,
    }
    coverage = {
        "window_days": 7,
        "days_marked_complete": len(complete_dates),
        "days_with_meals": len(by_day),
        "water_days_logged": hydration_summary["days_logged"],
        "days_with_complete_nutrition": sum(1 for day in tracked_days if day["kcal_complete"] and day["protein_complete"] and day["carbs_complete"] and day["fat_complete"]),
        "days_with_each_metric": metric_day_counts,
        "nutrition_source": "用户录入的包装标签或估算值；未补营养数据的餐次不会按零计算",
    }
    diagnosis = []
    warnings = []
    if hydration_summary["days_logged"]:
        diagnosis.append(
            f"近 7 天记录饮水 {hydration_summary['days_logged']} 天，累计 {hydration_summary['total_ml']} 毫升；有记录日均约 "
            f"{hydration_summary['average_on_logged_days_ml']} 毫升。未记录日期不按 0 计算，本工具不设统一饮水目标。"
        )
    else:
        diagnosis.append("近 7 天没有饮水量记录，暂时无法回顾饮水情况；可按需记录实际饮水量，本工具不设统一饮水目标。")
    if len(complete_dates) < 3:
        diagnosis.append("最近 7 天标记为完整的饮食记录少于 3 天，暂不根据记录计算日均差距；继续记录后再看趋势。")
    else:
        if averages["calories"] is None:
            diagnosis.append("完整日的能量信息仍不齐，暂时不能比较实际能量与目标。")
        elif averages["calories"] < bmr:
            warnings.append(f"最近完整记录日的平均摄入约 {averages['calories']} 千卡，低于估算 BMR {round(bmr)} 千卡。记录可能有漏项；若持续如此或正在刻意限制饮食，请优先保证健康并咨询专业人士。")
        else:
            diagnosis.append(f"完整记录日的平均能量约 {averages['calories']} 千卡，与目标 {calorie_target} 千卡相差约 {round(averages['calories']-calorie_target):+} 千卡。")
        if averages["protein"] is not None:
            diagnosis.append(f"完整记录日蛋白质日均约 {averages['protein']} 克，目标约 {macro_targets['protein_g']} 克，差约 {round(averages['protein']-macro_targets['protein_g']):+} 克。")
        else:
            diagnosis.append("蛋白质数据不完整，暂不判断是否达到目标。")
    if discrepancies:
        warnings.append("部分餐次的标注热量与按蛋白质/碳水/脂肪（4/4/9 千卡/克）推算值相差超过 25%；请核对份量或标签。")
    if protein_was_capped:
        warnings.append("按体重计算的蛋白质目标会超过目标能量的 35%，为避免宏量比例失衡已限制显示值；请让注册营养师结合体成分个别化评估。")
    if training_values and rest_values:
        training_day_comparison["carb_difference_g"] = round(training_day_comparison["training_day_carbs_g"] - training_day_comparison["rest_day_carbs_g"])
        diagnosis.append(f"已记录训练日碳水日均约 {training_day_comparison['training_day_carbs_g']} 克、休息日约 {training_day_comparison['rest_day_carbs_g']} 克（分别 {len(training_values)} 天与 {len(rest_values)} 天完整数据）；此差异仅描述记录，不代表优劣。")
    elif actual_training_dates:
        diagnosis.append("最近 7 天有训练记录，但训练日与休息日的完整碳水数据不足，暂不比较两类日期。")
    if profile.allergies or profile.avoid_foods:
        warnings.append("食物示例需由你逐项核对过敏原和忌口；文字匹配不能替代标签检查。")

    shares = [("早餐", 0.25), ("午餐", 0.35), ("晚餐", 0.30), ("加餐", 0.10)]
    meal_plan = [{
        "name": name,
        "calories_kcal": round(calorie_target * share),
        "protein_g": round(macro_targets["protein_g"] * share),
        "carbs_g": round(macro_targets["carbs_g"] * share),
        "fat_g": round(macro_targets["fat_g"] * share),
    } for name, share in shares]
    food_examples = [
        {"meal": "早餐", "example": "主食（燕麦或全麦面包）+ 蛋白质来源（鸡蛋、豆制品或乳品中选择适合你的）+ 水果"},
        {"meal": "午餐", "example": "米饭或杂粮饭 + 鱼、禽肉、豆腐等蛋白质来源 + 蔬菜"},
        {"meal": "晚餐", "example": "土豆、米饭等主食 + 鱼、蛋、豆制品或瘦肉 + 蔬菜"},
        {"meal": "加餐", "example": "按偏好选择水果、无糖乳品或豆制品；不饿时可不安排"},
    ]
    if profile.allergies or profile.avoid_foods:
        food_examples = [
            {"meal": "早餐", "example": "从你确认安全的食物中组合主食、蛋白质来源和水果/蔬菜；逐项核对包装与交叉污染提示。"},
            {"meal": "午餐", "example": "从你确认安全的主食、蛋白质来源和蔬菜中组合，并按本餐目标调整分量。"},
            {"meal": "晚餐", "example": "选择符合偏好的安全食材，包含主食、蛋白质来源和蔬菜；不确定时先核对标签。"},
            {"meal": "加餐", "example": "仅在需要时，从已确认安全的食物中选择。"},
        ]
    elif profile.cooking_access == "none":
        food_examples = [
            {"meal": "早餐", "example": "外食时按目标组合主食、蛋白质来源和水果；优先查看包装或菜单营养信息。"},
            {"meal": "午餐", "example": "选择含主食、蛋白质来源和蔬菜的套餐；酱汁可分开放，份量按本餐目标调整。"},
            {"meal": "晚餐", "example": "外食按主食、蛋白质来源和蔬菜搭配；根据预算选可持续的常见餐食。"},
            {"meal": "加餐", "example": "按偏好选择方便携带且确认适合自己的食品；不饿时可不安排。"},
        ]
    elif profile.dietary_preference and any(term in profile.dietary_preference.lower() for term in ("素食", "纯素", "vegan", "vegetarian")):
        food_examples = [
            {"meal": "早餐", "example": "燕麦或全麦面包 + 豆浆/豆腐等植物蛋白 + 水果"},
            {"meal": "午餐", "example": "米饭或杂粮饭 + 豆腐、豆类等植物蛋白 + 蔬菜"},
            {"meal": "晚餐", "example": "土豆、米饭等主食 + 豆类或豆制品 + 蔬菜"},
            {"meal": "加餐", "example": "按偏好选择水果、豆制品或坚果；不饿时可不安排"},
        ]
    training_info = {
        "frequency_days_per_week": training.days_per_week if training else None,
        "training_days": schedule.weekdays if schedule else None,
        "training_type": profile.training_type,
        "training_time": profile.training_time,
        "session_minutes": training.session_minutes if training else None,
    }
    if profile.training_time:
        if training_timing_review["days_last_meal_over_4h_before_training"]:
            diagnosis.append(f"在 {training_timing_review['days_with_meal_time_data']} 个同时有完整饮食和进食时间记录的训练日中，有 {training_timing_review['days_last_meal_over_4h_before_training']} 天记录到训练前超过 4 小时没有进食；这只是记录提示，可结合训练感受调整餐次。")
        else:
            diagnosis.append(f"训练时段档案为 {profile.training_time}；记录到 {training_timing_review['days_with_meal_time_data']} 个训练日有进食时间数据。可在训练前约 1–3 小时安排正常一餐，训练后约 1–2 小时按下一餐正常进食；无需强行加餐，并结合个人感受调整。")
    result = {
        "status": "ready",
        "summary": {
            "age_years": profile.age_years, "height_cm": body.height_cm, "weight_kg": body.weight_kg,
            "target_weight_kg": body.target_weight_kg,
            "weight_trend_14d": [{"date": row.recorded_on.isoformat(), "weight_kg": row.weight_kg} for row in weight_records],
            "weight_change_14d": round(weight_records[-1].weight_kg - weight_records[0].weight_kg, 1) if len(weight_records) >= 2 else None,
            "bmi": round(bmi, 1), "body_fat_percent": body.body_fat_percent,
            "muscle_mass_kg": profile.muscle_mass_kg,
            "bmr_kcal": round(bmr), "bmr_source": bmr_source,
            "tdee_kcal": round(tdee), "tdee_source": tdee_source,
            "goal": DIET_GOAL_LABELS[goal], "activity_level": DIET_ACTIVITY_LABELS[profile.activity_level],
            "training": training_info,
        },
        "record_summary": {
            "coverage": coverage, "averages": averages,
            "hydration": hydration_summary,
            "training_day_comparison": training_day_comparison,
            "meal_distribution": meal_distribution,
            "training_timing_review": training_timing_review,
        },
        "diagnosis": diagnosis,
        "warnings": warnings,
        "target": target,
        "meal_plan": meal_plan,
        "food_examples": food_examples,
        "execution_context": {
            "cooking_access": profile.cooking_access or "未填写",
            "eating_out_per_week": profile.eating_out_per_week,
            "budget_note": profile.budget_note,
            "dietary_preference": profile.dietary_preference,
        },
        "recorded_habits": {
            "keep": (
                "近 7 天重复记录：" + "、".join(f"{item['description']}（{item['count']} 次）" for item in common_meals)
                + "。重复仅表示你常选择这些餐食，不代表营养质量；可保留其中你确认适合且可持续的部分。"
                if common_meals else
                "最近 7 天还没有重复餐食记录，暂时不能识别稳定饮食习惯；继续记录后再比较。"
            ),
            "adjust": (
                f"完整记录显示蛋白质日均约 {averages['protein']} 克，低于当前估算目标约 {round(macro_targets['protein_g'] - averages['protein'])} 克；可把已确认安全的蛋白质来源分配到多餐，并用标签/称量记录复核。"
                if averages["protein"] is not None and averages["protein"] < macro_targets["protein_g"] else
                "优先调整完整记录中与目标差距最大的项目；营养数据不完整时先补记，不推断缺失摄入。"
            ),
        },
        "tracking": {
            "period": "连续记录并每 1–2 周回顾一次；可同时观察体重趋势、体脂率（如有）和训练感受。",
            "next_data": ["如有可靠来源，补充体脂率/肌肉量或设备测得的 BMR/TDEE", "尽量记录分量和包装标签营养数据", "每天确认是否已记录完整", "如希望回顾饮水情况，可记录实际饮水量；系统不设统一饮水目标"],
        },
        "assumptions": [
            "BMI 为成人筛查参考数值，不用于诊断。",
            "BMR/TDEE 是估算或用户提供的测量值，会受个体差异影响；请把目标作为起点而非精确处方。",
            "未提供实测 BMR 时使用 Mifflin–St Jeor：男性 10×体重kg + 6.25×身高cm − 5×年龄 + 5；女性末项为 −161。未提供实测 TDEE 时用 BMR 乘所选活动系数。",
            "每餐目标按早餐 25%、午餐 35%、晚餐 30%、加餐 10% 分配；可按作息调整，总量近似。",
            "当前没有内置食物营养数据库，食物示例不含精确营养值；实际分量以食品标签和称量记录为准，并核对过敏原。",
            "当前未采集微量营养素数据，不判断维生素或矿物质缺口；如有担忧请补充专业评估。",
        ],
    }
    with SessionLocal() as db:
        db.add(DietPlanSnapshotRecord(user_id=user_id, generated_on=date.today(), plan_data=result))
        db.commit()
    return result


@app.get("/api/diet/plan/history")
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


@app.delete("/api/diet/meal/{meal_id}")
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


@app.post("/api/diet/water")
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


# 保存一条训练日志，并拒绝早于本地档案起始日的记录。
@app.post("/api/log")
def create_log(payload: TrainingLog, user_id: int = Depends(authenticated_user_id)) -> dict:
    require_clear_safety_screen(user_id, payload.training_date)
    if payload.completion == "skipped" and payload.skip_reason is None:
        raise HTTPException(status_code=422, detail="未完成训练时，请选择未完成原因。")
    with SessionLocal() as db:
        registration_date = get_registration_date(db, user_id)
        if payload.training_date < registration_date:
            raise HTTPException(status_code=422, detail="训练日期早于本地档案起始日期，不能保存该记录。")
        plan_record = db.scalar(select(WeeklyPlanRecord).where(
            WeeklyPlanRecord.user_id == user_id,
            WeeklyPlanRecord.week_start == week_start_for(payload.training_date),
        ))
        schedule = serialize_today_schedule(
            plan_record.plan_data if plan_record is not None else None,
            payload.training_date,
        )
        planned_session = schedule.get("session") if schedule.get("status") == "training" else None
        planned_title = planned_session.get("title") if isinstance(planned_session, dict) else None
        record = TrainingLogRecord(
            user_id=user_id,
            **payload.model_dump(),
            planned_session_title=planned_title,
        )
        db.add(record)
        db.commit()
    entry = payload.model_dump(mode="json")
    entry["planned_session_title"] = planned_title
    plan_message = f"已关联计划训练：{planned_title}。" if planned_title else ""
    return {"ok": True, "log": entry, "message": "训练记录已保存到本机 PostgreSQL 数据库。" + plan_message}


# 根据记录日期读取对应周快照，供训练记录表单显示计划安排。
@app.get("/api/plan/session")
def plan_session_for_date(
    training_date: date | None = Query(default=None),
    user_id: int = Depends(authenticated_user_id),
) -> dict:
    selected_day = training_date or date.today()
    with SessionLocal() as db:
        registration_date = get_registration_date(db, user_id)
        if selected_day < registration_date:
            return {"training_date": selected_day.isoformat(), "status": "before_registration", "session": None}
        record = db.scalar(select(WeeklyPlanRecord).where(
            WeeklyPlanRecord.user_id == user_id,
            WeeklyPlanRecord.week_start == week_start_for(selected_day),
        ))
        schedule = serialize_today_schedule(record.plan_data if record is not None else None, selected_day)
    return {"training_date": selected_day.isoformat(), **schedule}


# 按日期倒序读取日志；查询结果不会早于本地档案起始日。
@app.get("/api/logs")
def list_logs(
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=500),
    user_id: int = Depends(authenticated_user_id),
) -> dict:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="开始日期不能晚于结束日期。")
    with SessionLocal() as db:
        registration_date = get_registration_date(db, user_id)
        query = select(TrainingLogRecord).where(TrainingLogRecord.user_id == user_id, TrainingLogRecord.training_date >= registration_date)
        if from_date:
            query = query.where(TrainingLogRecord.training_date >= from_date)
        if to_date:
            query = query.where(TrainingLogRecord.training_date <= to_date)
        records = db.scalars(
            query.order_by(TrainingLogRecord.training_date.desc(), TrainingLogRecord.id.desc())
            .limit(limit)
        ).all()
        items = [
            {
                "training_date": record.training_date.isoformat(),
                "completion": record.completion,
                "rpe": record.rpe,
                "skip_reason": record.skip_reason,
                "note": record.note,
                "planned_session_title": record.planned_session_title,
            }
            for record in records
        ]
    return {"items": items}


# 周回顾按七天汇总；缺少记录时显示未记录，不推断为休息或状态正常。
@app.get("/api/review/week")
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
