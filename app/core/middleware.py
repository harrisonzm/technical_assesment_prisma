from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from typing import Protocol

from redis.asyncio import Redis
from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class AsyncRedisClient(Protocol):
    async def get(self, key: str) -> bytes | str | None: ...
    async def set(self, key: str, value: str, *, ex: int) -> object: ...
    async def incr(self, key: str) -> int: ...
    async def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


class RedisResponseCacheMiddleware:
    """Redis-backed cache for successful GET responses, shared by all replicas."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        redis_url: str,
        ttl_seconds: int,
        key_prefix: str,
        path_prefix: str = "",
        redis_timeout_seconds: float = 0.2,
        redis_client: AsyncRedisClient | None = None,
    ) -> None:
        self.app = app
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix
        self.path_prefix = path_prefix
        self.redis: AsyncRedisClient = redis_client or Redis.from_url(
            redis_url,
            socket_connect_timeout=redis_timeout_seconds,
            socket_timeout=redis_timeout_seconds,
        )

    def _key(self, scope: Scope, version: str) -> str:
        raw = scope["path"].encode() + b"?" + scope.get("query_string", b"")
        digest = hashlib.sha256(raw).hexdigest()
        return f"{self.key_prefix}:v{version}:{digest}"

    @property
    def _version_key(self) -> str:
        return f"{self.key_prefix}:version"

    async def _version(self) -> str:
        value = await self.redis.get(self._version_key)
        if value is None:
            return "0"
        return value.decode() if isinstance(value, bytes) else value

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or self.ttl_seconds <= 0
            or not scope["path"].startswith(self.path_prefix)
        ):
            await self.app(scope, receive, send)
            return

        method = scope["method"].upper()
        if method != "GET":
            response_status: int | None = None

            async def track_send(message: Message) -> None:
                nonlocal response_status
                if message["type"] == "http.response.start":
                    response_status = int(message["status"])
                await send(message)

            await self.app(scope, receive, track_send)
            if response_status is not None and response_status < 400:
                try:
                    await self.redis.incr(self._version_key)
                except Exception:
                    pass  # Redis must never make successful writes fail.
            return

        try:
            version = await self._version()
            key = self._key(scope, version)
            raw_cached = await self.redis.get(key)
            cached = json.loads(raw_cached) if raw_cached is not None else None
        except Exception:
            version = "0"
            key = self._key(scope, version)
            cached = None

        if cached is not None:
            headers = [
                (base64.b64decode(name), base64.b64decode(value))
                for name, value in cached["headers"]
            ]
            mutable = MutableHeaders(raw=headers)
            mutable["X-Cache"] = "HIT"
            await send({"type": "http.response.start", "status": cached["status"], "headers": headers})
            await send({"type": "http.response.body", "body": base64.b64decode(cached["body"])})
            return

        start_message: Message | None = None
        body_parts: list[bytes] = []
        complete = False

        async def capture_send(message: Message) -> None:
            nonlocal start_message, complete
            if message["type"] == "http.response.start":
                start_message = message
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                complete = not message.get("more_body", False)
            await send(message)

        await self.app(scope, receive, capture_send)
        if start_message is None or not complete or int(start_message["status"]) >= 400:
            return

        headers = list(start_message.get("headers", []))
        cache_control = MutableHeaders(raw=headers).get("cache-control", "")
        if "no-store" in cache_control.lower():
            return

        entry = json.dumps(
            {
                "status": int(start_message["status"]),
                "headers": [
                    [base64.b64encode(name).decode(), base64.b64encode(value).decode()]
                    for name, value in headers
                ],
                "body": base64.b64encode(b"".join(body_parts)).decode(),
            },
            separators=(",", ":"),
        )
        try:
            await self.redis.set(key, entry, ex=self.ttl_seconds)
        except Exception:
            pass  # Fail open when Redis is temporarily unavailable.


class RedisRateLimitMiddleware:
    """Distributed fixed-window rate limiter backed by an atomic Redis script."""

    _SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {count, ttl}
"""

    def __init__(
        self,
        app: ASGIApp,
        *,
        redis_url: str,
        requests: int,
        window_seconds: int,
        key_prefix: str,
        path_prefix: str = "",
        redis_timeout_seconds: float = 0.2,
        redis_client: AsyncRedisClient | None = None,
    ) -> None:
        self.app = app
        self.requests = requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self.path_prefix = path_prefix
        self.redis: AsyncRedisClient = redis_client or Redis.from_url(
            redis_url,
            socket_connect_timeout=redis_timeout_seconds,
            socket_timeout=redis_timeout_seconds,
        )

    def _client_key(self, scope: Scope) -> str:
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        digest = hashlib.sha256(client_ip.encode()).hexdigest()
        return f"{self.key_prefix}:{digest}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or self.requests <= 0
            or not scope["path"].startswith(self.path_prefix)
        ):
            await self.app(scope, receive, send)
            return

        try:
            result = await self.redis.eval(
                self._SCRIPT,
                1,
                self._client_key(scope),
                self.window_seconds,
            )
            count, ttl = int(result[0]), max(1, int(result[1]))  # type: ignore[index]
        except Exception:
            await self.app(scope, receive, send)
            return

        remaining = max(0, self.requests - count)
        if count > self.requests:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests",
                    }
                },
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                },
            )
            await response(scope, receive, send)
            return

        async def add_rate_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-RateLimit-Limit"] = str(self.requests)
                headers["X-RateLimit-Remaining"] = str(remaining)
                headers["X-RateLimit-Reset"] = str(ttl)
            await send(message)

        await self.app(scope, receive, add_rate_headers)


class RequestQueueMiddleware:
    """Bound concurrent work and queue excess requests with a timeout."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_concurrency: int,
        max_queue_size: int,
        timeout_seconds: float,
    ) -> None:
        self.app = app
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_queue_size = max_queue_size
        self._timeout_seconds = timeout_seconds
        self._waiting = 0
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        queued = self._semaphore.locked()
        if queued:
            async with self._lock:
                if self._waiting >= self._max_queue_size:
                    await self._reject(scope, receive, send, 429, "request_queue_full")
                    return
                self._waiting += 1

        try:
            try:
                await asyncio.wait_for(self._semaphore.acquire(), self._timeout_seconds)
            except TimeoutError:
                await self._reject(scope, receive, send, 503, "request_queue_timeout")
                return
        finally:
            if queued:
                async with self._lock:
                    self._waiting -= 1

        try:
            await self.app(scope, receive, send)
        finally:
            self._semaphore.release()

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        status_code: int,
        code: str,
    ) -> None:
        response = JSONResponse(
            status_code=status_code,
            content={"error": {"code": code, "message": "Request queue is saturated"}},
            headers={"Retry-After": "1"},
        )
        await response(scope, receive, send)
