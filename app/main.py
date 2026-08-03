import time
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import router as api_v1_router
from app.core.Exceptions.Handlers.register import register_error_handlers
from app.core.Exceptions.RequestError import DatabaseUnavailableError
from app.core.config.config import Settings, get_settings
from app.core.config.logging import emit_log
from app.core.config.request_context import build_request_context, reset_context, set_context
from app.core.middleware import (
    RedisRateLimitMiddleware,
    RedisResponseCacheMiddleware,
    RequestQueueMiddleware,
)
from app.db.session import get_db_session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None if settings.is_prod else "/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )
    app.add_middleware(
        RedisResponseCacheMiddleware,
        redis_url=settings.redis_url,
        redis_timeout_seconds=settings.redis_timeout_seconds,
        ttl_seconds=settings.cache_ttl_seconds,
        key_prefix=settings.cache_key_prefix,
        path_prefix=settings.api_v1_prefix,
    )
    app.add_middleware(GZipMiddleware, minimum_size=settings.gzip_minimum_size)
    app.add_middleware(
        RequestQueueMiddleware,
        max_concurrency=settings.request_max_concurrency,
        max_queue_size=settings.request_queue_size,
        timeout_seconds=settings.request_queue_timeout_seconds,
    )
    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_url=settings.redis_url,
        redis_timeout_seconds=settings.redis_timeout_seconds,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        key_prefix=settings.rate_limit_key_prefix,
        path_prefix=settings.api_v1_prefix,
    )
    
    register_error_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.middleware("http")
    async def structured_logging_middleware(request: Request, call_next):
        context = build_request_context(request)
        context_token = set_context(context)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            level = "error" if response.status_code >= 500 else "info"
            response.headers["X-Request-ID"] = context.request_id
            emit_log(
                service=settings.service_name,
                level=level,
                message="request completed",
                method=request.method,
                endpoint=str(request.url.path),
                status_code=response.status_code,
                elapsed_ms=elapsed_ms,
            )
            return response
        except Exception as exc:  # pragma: no cover - defensive logging
            elapsed_ms = (time.perf_counter() - start) * 1000
            emit_log(
                service=settings.service_name,
                level="error",
                message="request failed",
                method=request.method,
                endpoint=str(request.url.path),
                status_code=500,
                elapsed_ms=elapsed_ms,
                error=exc,
            )
            raise
        finally:
            reset_context(context_token)

    @app.get("/health")
    def health(config: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
        emit_log(
            service=settings.service_name,
            level="info",
            message="health check ok",
            endpoint="/health",
            status_code=200,
        )
        return {
            "status": "ok",
        }

    @app.get("/health/ready")
    async def health_db(db: DbSession) -> dict[str, str]:
        try:
            await db.execute(text("SELECT 1"))
            emit_log(
                service=settings.service_name,
                level="info",
                message="database readiness check ok",
                endpoint="/health/ready",
                status_code=200,
            )
            return {
                "status": "ready",
            }
        except Exception as exc:
            emit_log(
                service=settings.service_name,
                level="error",
                message="database readiness check failed",
                endpoint="/health/ready",
                status_code=503,
                error=exc,
            )
            raise DatabaseUnavailableError(
                "Database is unavailable",
            ) from exc

    return app


app = create_app()
