from unittest.mock import MagicMock

import httpx

from app.consumer import process_batch, request_with_retry
from app.core.config.config import Settings


def build_settings(**overrides) -> Settings:
    values = {
        "service_name": "consumer",
        "consumer_api_url": "http://backend:8000/api/v1",
        "consumer_timeout_seconds": 1,
        "consumer_max_retries": 2,
        "consumer_retry_delay_seconds": 0.01,
        "consumer_batch_size": 3,
    }
    values.update(overrides)
    return Settings(**values)


def test_request_with_retry_retries_5xx_until_success():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503 if attempts < 3 else 201, request=request)

    sleep = MagicMock()
    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://backend:8000/api/v1",
    ) as client:
        response = request_with_retry(
            client,
            build_settings(),
            "POST",
            "/solicitudes",
            request_id="EXT-001",
            correlation_id="12345678-1234-5678-1234-567812345678",
            json={"external_id": "EXT-001"},
            sleep=sleep,
        )

    assert response is not None
    assert response.status_code == 201
    assert attempts == 3
    assert sleep.call_count == 2


def test_request_with_retry_retries_connection_errors():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, request=request)

    sleep = MagicMock()
    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://backend:8000/api/v1",
    ) as client:
        response = request_with_retry(
            client,
            build_settings(),
            "GET",
            "/solicitudes/123",
            request_id="EXT-001",
            correlation_id="12345678-1234-5678-1234-567812345678",
            sleep=sleep,
        )

    assert response is not None
    assert response.status_code == 200
    assert attempts == 2
    sleep.assert_called_once_with(0.01)


def test_request_with_retry_does_not_retry_4xx():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(422, request=request)

    sleep = MagicMock()
    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://backend:8000/api/v1",
    ) as client:
        response = request_with_retry(
            client,
            build_settings(consumer_max_retries=5),
            "POST",
            "/solicitudes",
            request_id="EXT-INVALID",
            correlation_id="12345678-1234-5678-1234-567812345678",
            json={"invalid": True},
            sleep=sleep,
        )

    assert response is not None
    assert response.status_code == 422
    assert attempts == 1
    sleep.assert_not_called()


def test_process_batch_continues_after_a_definitive_failure():
    post_attempts = 0
    get_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal post_attempts, get_attempts
        if request.method == "POST":
            post_attempts += 1
            if post_attempts == 1:
                return httpx.Response(400, request=request)
            return httpx.Response(
                201,
                request=request,
                json={"id": f"created-{post_attempts}"},
            )

        get_attempts += 1
        return httpx.Response(200, request=request, json={"state": "Recibida"})

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://backend:8000/api/v1",
    ) as client:
        created, queried = process_batch(
            client,
            build_settings(),
            batch_id="12345678-1234-5678-1234-567812345678",
            sleep=MagicMock(),
        )

    assert created == 2
    assert queried == 2
    assert post_attempts == 3
    assert get_attempts == 2
