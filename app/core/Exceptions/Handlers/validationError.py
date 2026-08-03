from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config.request_context import get_context
from app.schemas.errors import create_error_response


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    context = get_context()

    return create_error_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details={"errors": exc.errors()},
        request_id=context.request_id if context else None,
    )
