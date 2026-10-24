"""HTTP endpoints for auth."""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select, text
from ..core.security import hash_password, verify_password
from ..database import AccountUserRecord, claim_legacy_data_for_first_user, initialize_user_defaults
from ..schemas.auth import RegisterRequest, LoginRequest, DeleteAccountRequest
from ..services.safety_service import SCREENING_DATES


def serialize_auth_user(user):
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "is_admin": user.is_admin}

def create_auth_router(authenticated_user_id, session_factory):
    router = APIRouter()
    SessionLocal = session_factory

    @router.post("/api/auth/register")
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
                is_admin=False,
            )
            db.add(user)
            db.flush()
            if account_count == 0:
                claim_legacy_data_for_first_user(db, user.id)
            initialize_user_defaults(db, user.id, date.today())
            db.commit()
            user_id = user.id
            user_data = serialize_auth_user(user)
        request.session.clear()
        request.session["user_id"] = user_id
        SCREENING_DATES.pop(user_id, None)
        return {"user": user_data}

    @router.post("/api/auth/login")
    def login_account(payload: LoginRequest, request: Request) -> dict:
        username = payload.username.strip().lower()
        with SessionLocal() as db:
            user = db.scalar(select(AccountUserRecord).where(AccountUserRecord.username == username))
            if user is None or not verify_password(payload.password, user.password_salt, user.password_hash):
                # Use the same response for unknown usernames and incorrect passwords.
                verify_password(payload.password, "00" * 24, "00" * 64)
                raise HTTPException(status_code=401, detail="用户名或密码不正确。")
            user_id = user.id
            user_data = serialize_auth_user(user)
        request.session.clear()
        request.session["user_id"] = user_id
        SCREENING_DATES.pop(user_id, None)
        return {"user": user_data}

    @router.get("/api/auth/me")
    def current_account(user_id: int = Depends(authenticated_user_id)) -> dict:
        with SessionLocal() as db:
            user = db.get(AccountUserRecord, user_id)
            if user is None:
                raise HTTPException(401, "登录状态已失效，请重新登录。")
            return {"user": serialize_auth_user(user)}

    @router.post("/api/auth/logout")
    def logout_account(request: Request, user_id: int = Depends(authenticated_user_id)) -> dict:
        request.session.clear()
        SCREENING_DATES.pop(user_id, None)
        return {"ok": True}

    @router.delete("/api/auth/account")
    def delete_account(payload: DeleteAccountRequest, request: Request,
                       user_id: int = Depends(authenticated_user_id)) -> dict:
        # Only delete the signed-in account; account id is never accepted from the client.
        with SessionLocal() as db:
            user = db.scalar(select(AccountUserRecord).where(
                AccountUserRecord.id == user_id).with_for_update())
            if user is None:
                raise HTTPException(status_code=401, detail="登录状态已失效，请重新登录。")
            if not verify_password(payload.password, user.password_salt, user.password_hash):
                raise HTTPException(status_code=403, detail="当前密码不正确，账号未注销。")
            # All account-owned tables reference account_users with ON DELETE CASCADE.
            # Photos are stored in the database; shared exercises/knowledge remain untouched.
            # A failure rolls back the whole transaction, including the account deletion.
            db.delete(user)
            db.commit()
        request.session.clear()
        SCREENING_DATES.pop(user_id, None)
        return {"ok": True}

    return router
