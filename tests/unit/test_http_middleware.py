import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.core.middleware import (
    RedisRateLimitMiddleware,
    RedisResponseCacheMiddleware,
    RequestQueueMiddleware,
)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, bytes] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int):
        self.values[key] = value.encode()
        return True

    async def incr(self, key: str):
        value = int(self.values.get(key, b"0")) + 1
        self.values[key] = str(value).encode()
        return value


class FakeRateLimitRedis:
    def __init__(self):
        self.count = 0

    async def eval(self, script: str, numkeys: int, *keys_and_args: object):
        self.count += 1
        return [self.count, 60]


@pytest.mark.asyncio
async def test_get_responses_are_cached_and_writes_invalidate_cache():
    calls = 0
    app = FastAPI()

    @app.get("/resource")
    async def get_resource():
        nonlocal calls
        calls += 1
        return {"calls": calls}

    @app.post("/resource")
    async def update_resource():
        return {"ok": True}

    app.add_middleware(
        RedisResponseCacheMiddleware,
        redis_url="redis://unused",
        redis_client=FakeRedis(),
        ttl_seconds=60,
        key_prefix="test:http-cache",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.get("/resource")
        cached = await client.get("/resource")
        await client.post("/resource")
        refreshed = await client.get("/resource")

    assert first.json() == {"calls": 1}
    assert cached.json() == {"calls": 1}
    assert cached.headers["x-cache"] == "HIT"
    assert refreshed.json() == {"calls": 2}


@pytest.mark.asyncio
async def test_gzip_compresses_large_payloads():
    app = FastAPI()

    @app.get("/large")
    async def large_response():
        return {"value": "x" * 2_000}

    app.add_middleware(GZipMiddleware, minimum_size=100)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/large", headers={"Accept-Encoding": "gzip"})

    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["value"] == "x" * 2_000


@pytest.mark.asyncio
async def test_request_queue_rejects_when_queue_is_full():
    started = asyncio.Event()
    release = asyncio.Event()
    app = FastAPI()

    @app.get("/slow")
    async def slow_response():
        started.set()
        await release.wait()
        return {"ok": True}

    app.add_middleware(
        RequestQueueMiddleware,
        max_concurrency=1,
        max_queue_size=0,
        timeout_seconds=1,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        first_task = asyncio.create_task(client.get("/slow"))
        await started.wait()
        rejected = await client.get("/slow")
        release.set()
        first = await first_task

    assert first.status_code == 200
    assert rejected.status_code == 429
    assert rejected.json()["error"]["code"] == "request_queue_full"


@pytest.mark.asyncio
async def test_rate_limit_rejects_requests_over_the_redis_counter_limit():
    app = FastAPI()

    @app.get("/api/v1/resource")
    async def resource():
        return {"ok": True}

    app.add_middleware(
        RedisRateLimitMiddleware,
        redis_url="redis://unused",
        redis_client=FakeRateLimitRedis(),
        requests=2,
        window_seconds=60,
        key_prefix="test:rate-limit",
        path_prefix="/api/v1",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.get("/api/v1/resource")
        second = await client.get("/api/v1/resource")
        rejected = await client.get("/api/v1/resource")

    assert first.status_code == 200
    assert first.headers["x-ratelimit-remaining"] == "1"
    assert second.headers["x-ratelimit-remaining"] == "0"
    assert rejected.status_code == 429
    assert rejected.headers["retry-after"] == "60"
    assert rejected.json()["error"]["code"] == "rate_limit_exceeded"
