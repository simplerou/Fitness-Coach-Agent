"""Local-only administrator provisioning. No public API can assign roles."""
import argparse
import getpass
import secrets
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text
from app.database import AccountUserRecord, SessionLocal, engine, initialize_user_defaults
from app.core.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="本机管理员账号管理")
    parser.add_argument("action", choices=["create", "grant", "revoke"])
    parser.add_argument("username")
    parser.add_argument("--generate-password", action="store_true",
                        help="创建账号时生成随机密码，仅显示一次")
    args = parser.parse_args()
    username = args.username.strip().lower()
    from app.schemas.auth import RegisterRequest
    if args.action != "create" and args.generate_password:
        parser.error("--generate-password 仅用于 create")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE account_users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"))
    password = None
    if args.action == "create":
        password = secrets.token_urlsafe(18) if args.generate_password else getpass.getpass("管理员密码（至少8位）：")
        if not args.generate_password and password != getpass.getpass("再次输入密码："):
            parser.error("两次密码不一致")
        RegisterRequest(username=username, password=password, display_name="青禾管理员")
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(748219036)"))
        user = db.scalar(select(AccountUserRecord).where(AccountUserRecord.username == username).with_for_update())
        if args.action == "create":
            if user is not None:
                parser.error("用户名已存在，请使用 grant 或选择其他用户名")
            salt, digest = hash_password(password)
            user = AccountUserRecord(username=username, display_name="青禾管理员",
                                     password_salt=salt, password_hash=digest, is_admin=True)
            db.add(user)
            db.flush()
            initialize_user_defaults(db, user.id, date.today())
        else:
            if user is None:
                parser.error("账号不存在")
            user.is_admin = args.action == "grant"
        db.commit()
    print("管理员操作完成：" + args.action + " " + username)
    if args.action == "create" and args.generate_password:
        print("初始随机密码（请妥善保存）：" + password)


if __name__ == "__main__":
    main()
