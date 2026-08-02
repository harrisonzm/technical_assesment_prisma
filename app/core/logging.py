from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.request_context import get_context


def build_log_event(
    *,
    service: str,
    level: str,
    message: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    method: str | None = None,
    endpoint: str | None = None,
    status_code: int | None = None,
    elapsed_ms: float | None = None,
    attempt: int | None = None,
    error: Exception | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "level": level.upper(),
        "message": message,
    }

    context = get_context()
    effective_request_id = request_id or (context.request_id if context else None)
    if effective_request_id:
        event["request_id"] = effective_request_id

    effective_correlation_id = correlation_id or (context.correlation_id if context else None)
    if effective_correlation_id:
        event["correlation_id"] = effective_correlation_id

    if method:
        event["method"] = method

    if endpoint:
        event["endpoint"] = endpoint

    if status_code is not None:
        event["status_code"] = status_code

    if elapsed_ms is not None:
        event["elapsed_ms"] = round(elapsed_ms, 3)

    if attempt is not None:
        event["attempt"] = attempt

    if error is not None:
        event["error"] = {
            "type": error.__class__.__name__,
            "detail": str(error),
        }

    return event


def emit_log(
    *,
    service: str,
    level: str,
    message: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
    method: str | None = None,
    endpoint: str | None = None,
    status_code: int | None = None,
    elapsed_ms: float | None = None,
    attempt: int | None = None,
    error: Exception | None = None,
) -> None:
    event = build_log_event(
        service=service,
        level=level,
        message=message,
        request_id=request_id,
        correlation_id=correlation_id,
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        elapsed_ms=elapsed_ms,
        attempt=attempt,
        error=error,
    )

    output = json.dumps(event, ensure_ascii=False, default=str)
    print(output, flush=True)

    log_file_path = os.getenv("LOG_FILE_PATH")
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            try:
                os.makedirs(log_dir, exist_ok=True)
                with open(log_file_path, "a", encoding="utf-8") as handle:
                    handle.write(output + "\n")
            except OSError as exc:
                fallback_event = build_log_event(
                    service=service,
                    level="warning",
                    message="failed to write structured log file",
                    request_id=request_id,
                    correlation_id=correlation_id,
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    elapsed_ms=elapsed_ms,
                    attempt=attempt,
                    error=exc,
                )
                print(json.dumps(fallback_event, ensure_ascii=False, default=str), file=sys.stderr, flush=True)
