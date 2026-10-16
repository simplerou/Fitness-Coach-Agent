"""账号密码散列工具；原始密码不会写入数据库或日志。"""
from __future__ import annotations

import hashlib
import hmac
import secrets

PASSWORD_HASH_ITERATIONS = 310_000


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS, dklen=64)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hash)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS, dklen=64)
    return hmac.compare_digest(actual, expected)