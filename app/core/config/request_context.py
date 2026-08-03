from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import Request


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    correlation_id: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar(
    "request_context",
    default=None,
)


def normalize_uuid(value: str | None) -> str | None:
    """Return a normalized UUID or ignore an invalid external value."""
    if value is None:
        return None

    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        return None


def build_request_context(request: Request) -> RequestContext:
    """Build trusted request metadata from internal and external sources."""
    return RequestContext(
        request_id=str(uuid4()),
        correlation_id=normalize_uuid(request.headers.get("x-correlation-id")),
    )


def set_context(context: RequestContext) -> Token[RequestContext | None]:
    return _request_context.set(context)


def get_context() -> RequestContext | None:
    return _request_context.get()


def reset_context(token: Token[RequestContext | None]) -> None:
    _request_context.reset(token)
