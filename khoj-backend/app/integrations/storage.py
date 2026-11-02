"""Private R2 objects with SigV4 URLs; signed local reads for development only.

Uses the S3-compatible HTTP API directly, so no AWS credentials/SDK are needed.
Local cache files contain audio only; source text is never written to disk.
"""

import asyncio
import hashlib
import hmac
import os
import re
import time
from datetime import UTC, datetime
from urllib.parse import quote, urlencode, urlsplit
from uuid import uuid4

import httpx

from app.config import Settings
from app.core.errors import AppError


def tts_key(text: str, lang: str, voice: str, model: str, speed: float) -> str:
    return hashlib.sha256(f"{text}|{lang}|{voice}|{model}|{speed}".encode()).hexdigest()


class Storage:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.remote = bool(settings.r2_endpoint)
        if not self.remote and settings.env not in {"development", "test"}:
            raise ValueError("R2 must be configured outside development/test")
        if self.remote and not (
            settings.r2_access_key_id.get_secret_value()
            and settings.r2_secret_access_key.get_secret_value()
        ):
            raise ValueError("R2 credentials are required when R2_ENDPOINT is set")
        self._c = httpx.AsyncClient(transport=transport, timeout=30)

    def _validate(self, key: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise AppError("not_found", "Audio not found.", 404)

    def _local_signature(self, key: str, expires: int) -> str:
        return hmac.new(
            self.settings.jwt_secret.get_secret_value().encode(),
            f"tts:{key}:{expires}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def signed_url(self, key: str, base_url: str = "") -> str:
        self._validate(key)
        if self.remote:
            return self._r2_url("GET", key)
        expires = int(time.time()) + self.settings.tts_url_ttl
        signature = self._local_signature(key, expires)
        return (
            f"{base_url.rstrip('/')}/api/voice/cache/{key}?expires={expires}&signature={signature}"
        )

    def verify(self, key: str, expires: int, signature: str) -> None:
        self._validate(key)
        if (
            self.remote
            or expires <= time.time()
            or not hmac.compare_digest(self._local_signature(key, expires), signature)
        ):
            raise AppError("forbidden", "Audio link has expired or is invalid.", 403)

    def _r2_url(self, method: str, key: str, *, photo: bool = False) -> str:
        """S3 SigV4 query authentication; R2 region is `auto`."""
        now = datetime.now(UTC)
        stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
        endpoint = self.settings.r2_endpoint.rstrip("/")
        host = urlsplit(endpoint).netloc
        object_path = f"photos/{key}.jpg" if photo else f"tts/{key}.mp3"
        path = f"/{quote(self.settings.r2_bucket, safe='')}/{object_path}"
        scope = f"{day}/auto/s3/aws4_request"
        params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.settings.r2_access_key_id.get_secret_value()}/{scope}",
            "X-Amz-Date": stamp,
            "X-Amz-Expires": str(self.settings.tts_url_ttl),
            "X-Amz-SignedHeaders": "host",
        }
        query = urlencode(sorted(params.items()), quote_via=quote, safe="~")
        canonical = f"{method}\n{path}\n{query}\nhost:{host}\n\nhost\nUNSIGNED-PAYLOAD"
        to_sign = (
            f"AWS4-HMAC-SHA256\n{stamp}\n{scope}\n{hashlib.sha256(canonical.encode()).hexdigest()}"
        )
        signing_key = ("AWS4" + self.settings.r2_secret_access_key.get_secret_value()).encode()
        for part in (day, "auto", "s3", "aws4_request"):
            signing_key = hmac.new(signing_key, part.encode(), hashlib.sha256).digest()
        signature = hmac.new(signing_key, to_sign.encode(), hashlib.sha256).hexdigest()
        return f"{endpoint}{path}?{query}&X-Amz-Signature={signature}"

    async def get(self, key: str) -> bytes | None:
        self._validate(key)
        if self.remote:
            response = await self._c.get(self._r2_url("GET", key))
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.content
        try:
            return await asyncio.to_thread((self.settings.tts_cache_dir / f"{key}.mp3").read_bytes)
        except FileNotFoundError:
            return None

    async def put(self, key: str, data: bytes) -> None:
        self._validate(key)
        if self.remote:
            response = await self._c.put(
                self._r2_url("PUT", key), content=data, headers={"Content-Type": "audio/mpeg"}
            )
            response.raise_for_status()
        else:
            await asyncio.to_thread(self._put_local, key, data)

    def _put_local(self, key: str, data: bytes) -> None:
        directory = self.settings.tts_cache_dir
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = directory / f".{uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as stream:
                os.chmod(temporary, 0o600)
                stream.write(data)
            temporary.replace(directory / f"{key}.mp3")
        finally:
            temporary.unlink(missing_ok=True)

    async def aclose(self) -> None:
        await self._c.aclose()

    async def put_photo(self, key: str, data: bytes) -> None:
        self._validate(key)
        if self.remote:
            response = await self._c.put(
                self._r2_url("PUT", key, photo=True),
                content=data,
                headers={"Content-Type": "image/jpeg"},
            )
            response.raise_for_status()
        else:
            await asyncio.to_thread(self._photo_local, key, data)

    def _photo_local(self, key: str, data: bytes) -> None:
        directory = self.settings.tts_cache_dir.parent / "photos"
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / f"{key}.jpg"
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(data)
