from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging import emit_log
from app.core.request_context import get_context
from app.schemas.errors import create_error_response


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    context = get_context()

    emit_log(
        service="backend",
        level="error",
        message="unexpected application error",
        method=request.method,
        endpoint=request.url.path,
        status_code=500,
        error=exc,
    )

    return create_error_response(
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred",
        request_id=context.request_id if context else None,
    )
