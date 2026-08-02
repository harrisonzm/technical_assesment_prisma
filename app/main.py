import time
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.logging import emit_log
from app.core.request_context import build_request_context, reset_context, set_context


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
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        return {
            "status": "ok",
            "app": config.app_name,
            "environment": config.environment,
        }

    return app


app = create_app()
