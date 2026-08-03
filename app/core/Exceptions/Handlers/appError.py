from fastapi import Request
from fastapi.responses import JSONResponse

from ..AppError import AppError
from app.core.logging import emit_log
from app.core.request_context import get_context
from app.schemas.errors import create_error_response


async def app_error_handler(
    request: Request,
    exc: AppError,
) -> JSONResponse:
    context = get_context()

    emit_log(
        service="backend",
        level="warning",
        message=exc.message,
        method=request.method,
        endpoint=request.url.path,
        status_code=exc.status_code,
        error=exc,
    )

    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=context.request_id if context else None,
    )
