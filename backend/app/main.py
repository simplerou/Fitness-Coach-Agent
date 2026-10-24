"""FastAPI application wiring, session authentication and SPA hosting."""
from __future__ import annotations

from contextlib import asynccontextmanager
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .api.coach import create_coach_router
from .api.auth import create_auth_router
from .api.admin import create_admin_router
from .api.admin_knowledge import create_admin_knowledge_router
from .api.safety import create_safety_router
from .api.daily_signal import create_daily_signal_router
from .api.plan import create_plan_router
from .api.profile import create_profile_router
from .api.today import create_today_router
from .api.diet import create_diet_router
from .api.diet_plan import create_diet_plan_router
from .api.log import create_log_router
from .api.review import create_review_router
from .api.shaping import create_shaping_router
from .api.shaping_intelligence import create_shaping_intelligence_router
from .api.training_intelligence import create_training_intelligence_router
from .database import AccountUserRecord, SessionLocal, initialize_database
from .services.diet_targets import calculate_diet_targets
from .services.plan_service import week_start_for, serialize_today_schedule
from .services.profile_service import get_registration_date

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = PROJECT_ROOT / "web" / "dist"

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

app.include_router(create_coach_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_auth_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_admin_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_admin_knowledge_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_safety_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_daily_signal_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_plan_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_profile_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_today_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_diet_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_diet_plan_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_log_router(authenticated_user_id, lambda: SessionLocal()))
app.include_router(create_review_router(authenticated_user_id, lambda: SessionLocal()))

app.include_router(create_shaping_router(authenticated_user_id))
app.include_router(create_shaping_intelligence_router(
    authenticated_user_id,
    week_start_for,
    serialize_today_schedule,
    calculate_diet_targets,
))
app.include_router(create_training_intelligence_router(
    authenticated_user_id,
    get_registration_date,
    serialize_today_schedule,
    week_start_for,
))


@app.get("/{full_path:path}")
def spa_fallback(full_path: str) -> FileResponse:
    """Serve the Vite entry for browser routes; API and static paths keep their own routing."""
    if full_path.startswith(("api/", "static/")):
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(WEB_ROOT / "index.html")
