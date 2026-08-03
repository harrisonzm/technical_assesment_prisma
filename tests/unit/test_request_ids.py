from uuid import UUID

from starlette.requests import Request

from app.core.config.logging import build_log_event
from app.core.config.request_context import (
    RequestContext,
    build_request_context,
    normalize_uuid,
    reset_context,
    set_context,
)


def test_normalize_uuid_normalizes_valid_value():
    correlation_id = "A8098C1A-F86E-11DA-BD1A-00112444BE1E"

    assert normalize_uuid(correlation_id) == str(UUID(correlation_id))


def test_invalid_correlation_id_is_ignored():
    assert normalize_uuid("123") is None
    assert normalize_uuid(None) is None


def test_build_request_context_generates_internal_request_id():
    correlation_id = "a8098c1a-f86e-11da-bd1a-00112444be1e"
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"x-request-id", b"client-controlled"),
                (b"x-correlation-id", correlation_id.encode()),
            ],
        }
    )

    context = build_request_context(request)

    assert UUID(context.request_id)
    assert context.request_id != "client-controlled"
    assert context.correlation_id == correlation_id


def test_log_event_uses_request_context():
    token = set_context(
        RequestContext(
            request_id="internal-request-id",
            correlation_id="external-correlation-id",
        )
    )

    try:
        event = build_log_event(service="backend", level="info", message="hello")
    finally:
        reset_context(token)

    assert event["request_id"] == "internal-request-id"
    assert event["correlation_id"] == "external-correlation-id"
