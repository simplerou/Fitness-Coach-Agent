# FastAPI 应用入口：定义本机演示版 HTTP 接口，并连接页面与 PostgreSQL。
# 确认通过日期暂存于服务进程内；当日暂停状态、计划、状态和训练日志保存在数据库。
from __future__ import annotations

from contextlib import asynccontextmanager
import os
import secrets
from datetime import date, timedelta
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

from .database import (
    DEFAULT_TRAINING_WEEKDAYS_BY_COUNT,
    AccountUserRecord,
    DailySignalRecord,
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

    signals_by_day = {record.signal_date: record for record in signals}
    logs_by_day: dict[date, list[TrainingLogRecord]] = {}
    for record in logs:
        logs_by_day.setdefault(record.training_date, []).append(record)

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
        },
        "days": days,
    }
