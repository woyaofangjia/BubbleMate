"""
身份令牌：服务端签发、HMAC 签名，用于稳定 user_id 与管理端鉴权。

令牌格式：base64url("{subject}.{issued_at}.{hmac}")
- 用户令牌：subject = user_id，有效期 USER_TOKEN_TTL（默认 180 天）
- 管理令牌：subject = "admin"，有效期 ADMIN_TOKEN_TTL（默认 12 小时）
"""

import base64
import hashlib
import hmac
import os
import time
import uuid

SECRET = os.getenv("IDENTITY_SECRET", "bubblemate-dev-secret-change-me")
USER_TOKEN_TTL = int(os.getenv("USER_TOKEN_TTL", str(60 * 60 * 24 * 180)))
ADMIN_TOKEN_TTL = int(os.getenv("ADMIN_TOKEN_TTL", str(60 * 60 * 12)))


def _mac(subject: str, issued_at: str, kind: str) -> str:
    msg = f"{kind}:{subject}:{issued_at}".encode("utf-8")
    return hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:32]


def _issue(kind: str, subject: str, ttl: int) -> str:
    issued_at = str(int(time.time()))
    raw = f"{subject}.{issued_at}.{_mac(subject, issued_at, kind)}"
    token = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")
    return token.rstrip("=")


def _verify(kind: str, token: str, ttl: int) -> str | None:
    if not token:
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        subject, issued_at, signature = raw.rsplit(".", 2)
        expected = _mac(subject, issued_at, kind)
        if not hmac.compare_digest(signature, expected):
            return None
        if int(time.time()) - int(issued_at) > ttl:
            return None
        return subject
    except Exception:
        return None


def new_user_id() -> str:
    return f"u_{uuid.uuid4().hex[:16]}"


def issue_user_token(user_id: str) -> str:
    return _issue("user", user_id, USER_TOKEN_TTL)


def verify_user_token(token: str) -> str | None:
    return _verify("user", token, USER_TOKEN_TTL)


def issue_admin_token() -> str:
    return _issue("admin", "admin", ADMIN_TOKEN_TTL)


def verify_admin_token(token: str) -> bool:
    return _verify("admin", token, ADMIN_TOKEN_TTL) is not None


def extract_bearer(request) -> str:
    raw = request.headers.get("authorization", "") or ""
    if raw.lower().startswith("bearer "):
        return raw[7:].strip()
    return raw.strip()
