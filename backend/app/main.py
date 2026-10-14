from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select

from .database import (
    DailySignalRecord,
    SessionLocal,
    TrainingLogRecord,
    initialize_database,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web"


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Fitness Coach Agent", version="1.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")

# Safety hold and the generated plan remain in this local demo process. A restart
# clears them, so the user must complete the safety screen again.
STATE: dict = {
    "screening_complete": False,
    "safety_hold": False,
    "hold_requires_professional_confirmation": False,
    "plan": None,
}

SYMPTOM_LABELS = {
    "chest_pain": "胸痛或胸闷",
    "fainting": "晕厥或接近晕厥",
    "dizziness": "明显眩晕",
    "severe_joint_pain": "严重关节疼痛",
    "other_discomfort": "其他明显不适",
    "uncertain": "无法判断是否存在上述情况",
}


class SafetyCheck(BaseModel):
    completed: bool = False
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


class PlanRequest(BaseModel):
    goal: Literal["strength", "fitness", "fat_loss"] = "fitness"
    days_per_week: int = Field(default=3, ge=1, le=6)


class TrainingLog(BaseModel):
    training_date: date = Field(default_factory=date.today)
    completion: Literal["completed", "partial", "skipped"]
    rpe: int | None = Field(default=None, ge=1, le=10)
    skip_reason: Literal["no_time", "too_tired", "discomfort", "other"] | None = None
    note: str | None = Field(default=None, max_length=240)


def require_clear_safety_screen() -> None:
    if STATE["safety_hold"]:
        raise HTTPException(
            status_code=423,
            detail="安全暂停仍生效。请先按页面提示寻求专业意见并完成恢复确认。",
        )
    if not STATE["screening_complete"]:
        raise HTTPException(
            status_code=409,
            detail="请先完成今日安全筛查；未完成前不提供训练建议。",
        )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "1.1.0", "storage": "postgresql"}


@app.post("/api/safety-check")
def safety_check(payload: SafetyCheck) -> dict:
    if not payload.completed:
        STATE["screening_complete"] = False
        return {
            "status": "ask",
            "message": "请完成安全筛查。未完成或无法判断时，暂不生成训练建议。",
            "symptoms": [],
        }

    if payload.symptoms:
        STATE["screening_complete"] = False
        STATE["safety_hold"] = True
        STATE["hold_requires_professional_confirmation"] = True
        labels = [SYMPTOM_LABELS[item] for item in payload.symptoms]
        return {
            "status": "stop",
            "message": "请停止本次训练，不要依据本工具继续运动；胸部不适、晕厥、明显眩晕或严重疼痛等情况应及时寻求医疗帮助。",
            "symptoms": labels,
        }

    if STATE["safety_hold"]:
        return {
            "status": "stop",
            "message": "安全暂停仍生效。请先按专业意见确认恢复，再重新完成筛查。",
            "symptoms": [],
        }

    STATE["screening_complete"] = True
    return {
        "status": "clear",
        "message": "筛查已完成。本工具不能诊断疾病，也不能保证训练安全。",
        "symptoms": [],
    }


@app.post("/api/safety-resolution")
def safety_resolution(payload: SafetyResolution) -> dict:
    if not STATE["safety_hold"]:
        raise HTTPException(status_code=409, detail="当前没有待处理的安全暂停。")
    if not payload.confirmed_recovery or not payload.followed_professional_advice:
        raise HTTPException(
            status_code=400,
            detail="解除安全暂停前，需确认已恢复并遵循专业人士意见。",
        )
    STATE["safety_hold"] = False
    STATE["hold_requires_professional_confirmation"] = False
    STATE["screening_complete"] = False
    return {"status": "resolved", "message": "暂停已解除。请重新完成当日安全筛查。"}


@app.post("/api/daily-signal")
def save_daily_signal(payload: DailySignal) -> dict:
    require_clear_safety_screen()
    today = date.today()
    with SessionLocal() as db:
        record = db.get(DailySignalRecord, today)
        if record is None:
            record = DailySignalRecord(signal_date=today, **payload.model_dump())
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


@app.post("/api/plan")
def create_plan(payload: PlanRequest) -> dict:
    require_clear_safety_screen()
    focus = {
        "strength": "力量基础",
        "fitness": "综合体能",
        "fat_loss": "可持续活动",
    }[payload.goal]
    sessions = []
    for index in range(payload.days_per_week):
        if index % 2 == 0:
            title = "全身力量练习"
            description = "选择熟悉且无痛的推、拉、蹲或髋部动作，按个人能力安排。"
        else:
            title = "轻松有氧与活动度"
            description = "选择可以轻松交谈的活动强度；感觉不适时停止。"
        sessions.append({"day": f"训练日 {index + 1}", "title": title, "description": description})
    plan = {
        "goal": payload.goal,
        "focus": focus,
        "days_per_week": payload.days_per_week,
        "sessions": sessions,
        "notice": "这是用于验证流程的通用示例，不是医疗或个体化处方。请结合自身能力及专业人士意见调整。",
    }
    STATE["plan"] = plan
    return {"week_plan": plan, "explanations": [f"按你选择的目标“{focus}”和每周 {payload.days_per_week} 天生成基础模板。"]}


@app.get("/api/today")
def today() -> dict:
    if STATE["safety_hold"]:
        return {
            "level": "stop",
            "message": "安全暂停生效。请停止训练并按提示寻求专业帮助。",
            "plan_items": [],
            "reasons": ["安全筛查命中暂停条件"],
        }
    if not STATE["screening_complete"]:
        return {
            "level": "ask",
            "message": "请先完成今日安全筛查。",
            "plan_items": [],
            "reasons": ["今日安全筛查尚未完成"],
        }
    with SessionLocal() as db:
        signal_record = db.get(DailySignalRecord, date.today())
        signal = (
            {
                "readiness": signal_record.readiness,
                "sleep_hours": signal_record.sleep_hours,
                "resting_hr": signal_record.resting_hr,
            }
            if signal_record
            else None
        )
    if signal is None:
        return {
            "level": "insufficient_data",
            "message": "还没有记录今天的主观状态，暂时无法判断是否需要调整。",
            "plan_items": [],
            "reasons": ["今日状态数据未提供；缺失不代表状态正常"],
        }
    if signal["readiness"] == "poor":
        return {
            "level": "downgrade",
            "message": "你报告今天状态较差。考虑降低训练强度或休息；如有疼痛或明显不适，请停止训练并寻求专业帮助。",
            "plan_items": [],
            "reasons": ["依据：用户报告今日状态较差"],
        }
    return {
        "level": "normal",
        "message": "你报告今天状态尚可。按已确认的计划进行，不要因为本工具的结果临时加量。",
        "plan_items": STATE["plan"]["sessions"] if STATE["plan"] else [],
        "reasons": [f"依据：用户报告今日状态为 {'良好' if signal['readiness'] == 'good' else '一般'}"],
    }


@app.post("/api/log")
def create_log(payload: TrainingLog) -> dict:
    require_clear_safety_screen()
    if payload.completion == "skipped" and payload.skip_reason is None:
        raise HTTPException(status_code=422, detail="未完成训练时，请选择未完成原因。")
    with SessionLocal() as db:
        record = TrainingLogRecord(**payload.model_dump())
        db.add(record)
        db.commit()
    entry = payload.model_dump(mode="json")
    return {"ok": True, "log": entry, "message": "训练记录已保存到本机 PostgreSQL 数据库。"}


@app.get("/api/logs")
def list_logs() -> dict:
    with SessionLocal() as db:
        records = db.scalars(
            select(TrainingLogRecord)
            .order_by(TrainingLogRecord.training_date.desc(), TrainingLogRecord.id.desc())
            .limit(20)
        ).all()
        items = [
            {
                "training_date": record.training_date.isoformat(),
                "completion": record.completion,
                "rpe": record.rpe,
                "skip_reason": record.skip_reason,
                "note": record.note,
            }
            for record in records
        ]
    return {"items": items}
