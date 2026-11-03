"""Environment-only configuration; importing this module never opens sockets."""

import base64
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True, hide_input_in_errors=True
    )
    env: Literal["development", "test", "staging", "production"] = Field(
        default="development", validation_alias="KHOJ_ENV"
    )
    demo_auth: bool = True
    database_url: str = "postgresql+asyncpg://khoj:khoj@localhost:5432/khoj"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_urlsafe(48)))
    phone_hmac_secret: SecretStr = Field(
        default_factory=lambda: SecretStr(secrets.token_urlsafe(48))
    )
    phone_enc_key: SecretStr = Field(
        default_factory=lambda: SecretStr(
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        )
    )
    access_ttl_seconds: int = Field(default=900, ge=60, le=900)
    refresh_ttl_seconds: int = Field(default=2_592_000, ge=900)
    allowed_origins: str = "http://localhost:3000,https://localhost:3000"
    enable_pgvector: bool = False
    extraction_schema: Literal["v1", "v2"] = "v1"
    ollama_base: str = "https://ollama.com"
    ollama_key: SecretStr = Field(default=SecretStr(""), validation_alias="OLLAMA_API_KEY")
    gnani_base: str = "https://api.vachana.ai"
    gnani_key: SecretStr = Field(default=SecretStr(""), validation_alias="GNANI_API_KEY")
    gnani_stt_slots: int = Field(default=1, ge=1)
    gnani_tts_slots: int = Field(default=2, ge=1)
    tts_voice: str = Field(default="Shivani", validation_alias="KHOJ_TTS_VOICE")
    tts_model: str = "timbre-v3.0"
    tts_speed: float = Field(default=1.0, ge=0.85, le=1.15)
    tts_cache_dir: Path = ROOT / ".cache/tts"
    tts_url_ttl: int = Field(default=900, ge=1, le=604800)
    models_file: Path = Field(
        default=ROOT / "config/models.yaml", validation_alias="KHOJ_MODELS_FILE"
    )
    r2_endpoint: str = ""
    r2_access_key_id: SecretStr = SecretStr("")
    r2_secret_access_key: SecretStr = SecretStr("")
    r2_bucket: str = "khoj-private"
    contact: str = Field(default="", validation_alias="KHOJ_CONTACT")

    @model_validator(mode="after")
    def validate_security(self) -> Self:
        if self.env == "production" and self.demo_auth:
            raise ValueError("DEMO_AUTH must be off in production")
        if self.env != "test":
            required = {"jwt_secret", "phone_hmac_secret", "phone_enc_key"}
            if not required.issubset(self.model_fields_set):
                raise ValueError(
                    "Set JWT_SECRET, PHONE_HMAC_SECRET and PHONE_ENC_KEY in .env; run make env"
                )
        if (
            len(self.jwt_secret.get_secret_value()) < 32
            or len(self.phone_hmac_secret.get_secret_value()) < 32
        ):
            raise ValueError("JWT_SECRET and PHONE_HMAC_SECRET must have at least 32 characters")
        try:
            key = base64.b64decode(
                self.phone_enc_key.get_secret_value(), altchars=b"-_", validate=True
            )
        except ValueError as exc:
            raise ValueError("PHONE_ENC_KEY must be a base64-encoded 32-byte key") from exc
        if len(key) != 32:
            raise ValueError("PHONE_ENC_KEY must decode to 32 bytes")
        return self

    def models(self) -> dict[str, object]:
        with self.models_file.open() as stream:
            value: object = yaml.safe_load(stream)
        if not isinstance(value, dict):
            raise ValueError("Model routing config must be a mapping")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Compatibility with the supplied prototype Settings factory.
settings = Settings
