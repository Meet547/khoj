import secrets
from typing import Protocol

from app.core.errors import AppError


class OtpProvider(Protocol):
    demo: bool

    async def send(self, phone: str) -> None: ...
    async def verify(self, phone: str, code: str) -> bool: ...


class DemoOtpProvider:
    demo = True

    async def send(self, phone: str) -> None:
        # Deliberately no outbound message or plaintext phone persisted.
        return None

    async def verify(self, phone: str, code: str) -> bool:
        return secrets.compare_digest(code, "123456")


class UnconfiguredOtpProvider:
    demo = False

    async def send(self, phone: str) -> None:
        raise AppError(
            "otp_unavailable", "Sign-in is temporarily unavailable.", 503, retryable=True
        )

    async def verify(self, phone: str, code: str) -> bool:
        raise AppError(
            "otp_unavailable", "Sign-in is temporarily unavailable.", 503, retryable=True
        )
