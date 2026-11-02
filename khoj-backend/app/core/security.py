import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings
from app.core.errors import AppError


class PhoneVault:
    def __init__(self, settings: Settings):
        self._hmac_key = settings.phone_hmac_secret.get_secret_value().encode()
        self._cipher = AESGCM(base64.urlsafe_b64decode(settings.phone_enc_key.get_secret_value()))

    def digest(self, phone: str) -> bytes:
        return hmac.digest(self._hmac_key, phone.encode(), "sha256")

    def encrypt(self, phone: str) -> bytes:
        nonce = os.urandom(12)
        return nonce + self._cipher.encrypt(nonce, phone.encode(), b"khoj:phone:v1")

    def decrypt(self, encrypted: bytes) -> str:
        return self._cipher.decrypt(encrypted[:12], encrypted[12:], b"khoj:phone:v1").decode()


def token_digest(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def issue_access(settings: Settings, user_id: UUID, role: str, session_id: UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "jti": str(session_id),
            "iat": now,
            "exp": now + timedelta(seconds=settings.access_ttl_seconds),
            "iss": "khoj",
            "aud": "khoj-web",
        },
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )


def decode_access(settings: Settings, token: str) -> tuple[UUID, str, UUID]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer="khoj",
            audience="khoj-web",
            options={"require": ["exp", "iat", "sub", "role", "jti"]},
        )
        role = claims["role"]
        if role not in ("citizen", "volunteer", "officer", "admin"):
            raise ValueError("Invalid role")
        return UUID(claims["sub"]), str(role), UUID(claims["jti"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError) as exc:
        raise AppError("unauthorized", "Please sign in again.", 401) from exc
