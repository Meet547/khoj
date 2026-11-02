"""Authentication, voice and grounded model gateway; prototype search stays private."""

import hashlib
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.responses import Response

from app.api import admin, auth, gateway, health, intake, voice
from app.capabilities import Capabilities
from app.config import Settings, get_settings
from app.core.errors import AppError, error_response, install_handlers
from app.core.logging import configure_logging, request_id
from app.core.semaphore import RedisSemaphore
from app.graph.audio import IntakeAudio
from app.graph.resources import Resources
from app.graph.service import IntakeService
from app.integrations.gnani import Gnani
from app.integrations.ollama import OllamaClient
from app.integrations.sms import DemoOtpProvider, UnconfiguredOtpProvider
from app.integrations.storage import Storage
from app.llm import LLM
from app.usage import Usage

logger = logging.getLogger("khoj")


def create_app(
    settings: Settings | None = None,
    *,
    db_factory: async_sessionmaker[AsyncSession] | None = None,
    redis: Redis | None = None,
    gnani: Gnani | None = None,
    ollama: OllamaClient | None = None,
    storage: Storage | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        config = settings or get_settings()
        engine = (
            create_async_engine(config.database_url, pool_pre_ping=True, hide_parameters=True)
            if db_factory is None
            else None
        )
        app.state.settings = config
        app.state.db_factory = db_factory or async_sessionmaker(engine, expire_on_commit=False)
        app.state.redis = redis or Redis.from_url(config.redis_url)
        app.state.otp_provider = (
            DemoOtpProvider() if config.demo_auth else UnconfiguredOtpProvider()
        )
        account = hashlib.sha256(config.gnani_key.get_secret_value().encode()).hexdigest()[:16]
        app.state.gnani = gnani or Gnani(
            config.gnani_key.get_secret_value(),
            config.gnani_base,
            stt_slots=config.gnani_stt_slots,
            tts_slots=config.gnani_tts_slots,
            shared_stt=RedisSemaphore(
                app.state.redis, f"gnani:stt:{account}", config.gnani_stt_slots
            ),
        )
        app.state.ollama = ollama or OllamaClient(
            config.ollama_base, config.ollama_key.get_secret_value()
        )
        app.state.storage = storage or Storage(config)
        models = config.models()
        app.state.capabilities = Capabilities(app.state.ollama, models)
        app.state.usage = Usage(app.state.redis, models)
        app.state.llm = LLM(
            app.state.ollama, models, usage=app.state.usage, capabilities=app.state.capabilities
        )
        app.state.intake_resources = Resources()
        app.state.intake = IntakeService(
            config, app.state.db_factory, app.state.redis, app.state.llm, app.state.intake_resources
        )
        app.state.intake_audio = IntakeAudio(
            config,
            app.state.storage,
            app.state.gnani,
            app.state.intake_resources,
            app.state.db_factory,
        )
        await app.state.capabilities.probe()
        logger.info("api_started")
        try:
            yield
        finally:
            await app.state.intake_audio.close()
            await app.state.intake.close()
            if gnani is None:
                await cast(Gnani, app.state.gnani).aclose()
            if ollama is None:
                await cast(OllamaClient, app.state.ollama).aclose()
            if storage is None:
                await cast(Storage, app.state.storage).aclose()
            if redis is None:
                await cast(Redis, app.state.redis).aclose()
            if engine:
                await engine.dispose()

    app = FastAPI(
        title="KHOJ API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    install_handlers(app)

    @app.middleware("http")
    async def context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        correlation = incoming if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming) else uuid4().hex
        reset = request_id.set(correlation)
        try:
            config = cast(Settings, request.app.state.settings)
            origin = request.headers.get("origin")
            response: Response
            if request.method not in ("GET", "HEAD", "OPTIONS") and (
                request.headers.get("sec-fetch-site") == "cross-site"
                or (origin is not None and origin not in config.allowed_origins.split(","))
            ):
                response = error_response(
                    AppError("forbidden", "This request could not be verified.", 403)
                )
            else:
                try:
                    response = await call_next(request)
                except RedisError:
                    logger.error("redis_unavailable")
                    response = error_response(
                        AppError(
                            "temporarily_unavailable",
                            "Please try again in a moment.",
                            503,
                            retryable=True,
                        )
                    )
                except Exception:
                    logger.error("request_failed")
                    response = error_response(
                        AppError(
                            "internal_error",
                            "Something went wrong. Please try again.",
                            500,
                            retryable=True,
                        )
                    )
            response.headers["X-Request-ID"] = correlation
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Cache-Control"] = "no-store"
            logger.info("request_completed")
            return response
        finally:
            request_id.reset(reset)

    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(voice.router)
    app.include_router(gateway.router)
    app.include_router(admin.router)
    app.include_router(intake.router)
    return app


app = create_app()
