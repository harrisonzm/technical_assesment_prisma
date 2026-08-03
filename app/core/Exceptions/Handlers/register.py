from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.core.Exceptions.AppError import AppError
from app.core.Exceptions.Handlers.appError import app_error_handler
from app.core.Exceptions.Handlers.unexpectedError import unexpected_error_handler
from app.core.Exceptions.Handlers.validationError import validation_error_handler


def register_error_handlers(
    app: FastAPI
) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
    app.add_exception_handler(
        Exception,
        unexpected_error_handler,
    )
