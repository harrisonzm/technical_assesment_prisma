from __future__ import annotations

import os
import time

from app.core.config.config import Settings
from app.core.config.logging import emit_log


def main() -> None:
    settings = Settings()
    interval_seconds = float(settings.consumer_interval_seconds)
    attempt = 0

    while True:
        attempt += 1
        start = time.perf_counter()
        try:
            if os.getenv("CONSUMER_FAIL_ONCE", "false").lower() == "true" and attempt == 1:
                raise RuntimeError("simulated consumer failure")

            emit_log(
                service=settings.service_name,
                level="info",
                message="consumer processed event",
                request_id=f"consumer-{attempt}",
                method="CONSUMER",
                endpoint="/events",
                status_code=200,
                elapsed_ms=(time.perf_counter() - start) * 1000,
                attempt=attempt,
            )
        except Exception as exc:  # pragma: no cover - runtime guard
            emit_log(
                service=settings.service_name,
                level="error",
                message="consumer processing failed",
                request_id=f"consumer-{attempt}",
                method="CONSUMER",
                endpoint="/events",
                status_code=500,
                elapsed_ms=(time.perf_counter() - start) * 1000,
                attempt=attempt,
                error=exc,
            )

        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
