"""In-memory observability metrics for local service monitoring."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class MetricsRegistry:
    """Maintain lightweight counters and latency summaries in memory."""

    def __init__(self) -> None:
        self._http_requests: dict[str, int] = defaultdict(int)
        self._http_status_codes: dict[str, int] = defaultdict(int)
        self._http_paths: dict[str, int] = defaultdict(int)
        self._agent_runs: dict[str, int] = defaultdict(int)
        self._agent_failures: dict[str, int] = defaultdict(int)
        self._agent_latency_ms: dict[str, list[float]] = defaultdict(list)
        self._request_latency_ms: list[float] = []

    def record_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        key = f"{method}:{path}:{status_code}"
        self._http_requests[key] += 1
        self._http_status_codes[str(status_code)] += 1
        self._http_paths[f"{method}:{path}"] += 1
        self._request_latency_ms.append(duration_ms)

    def record_agent_run(
        self,
        *,
        name: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        self._agent_runs[name] += 1
        if not success:
            self._agent_failures[name] += 1
        self._agent_latency_ms[name].append(duration_ms)

    def snapshot(self) -> dict[str, Any]:
        total_requests = sum(self._http_requests.values())
        total_agent_runs = sum(self._agent_runs.values())
        total_agent_failures = sum(self._agent_failures.values())

        def average(values: list[float]) -> float:
            return round(sum(values) / len(values), 3) if values else 0.0

        return {
            "total_requests": total_requests,
            "total_agent_runs": total_agent_runs,
            "total_agent_failures": total_agent_failures,
            "http_requests": dict(sorted(self._http_requests.items())),
            "http_status_codes": dict(sorted(self._http_status_codes.items())),
            "http_paths": dict(sorted(self._http_paths.items())),
            "agent_runs": dict(sorted(self._agent_runs.items())),
            "agent_failures": dict(sorted(self._agent_failures.items())),
            "request_latency_ms": {
                "avg": average(self._request_latency_ms),
                "count": len(self._request_latency_ms),
            },
            "agent_latency_ms": {
                name: {
                    "avg": average(values),
                    "count": len(values),
                }
                for name, values in sorted(self._agent_latency_ms.items())
            },
        }


registry = MetricsRegistry()


def record_http_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
) -> None:
    registry.record_http_request(
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
    )


def record_agent_run(
    *,
    name: str,
    duration_ms: float,
    success: bool,
) -> None:
    registry.record_agent_run(
        name=name,
        duration_ms=duration_ms,
        success=success,
    )


def metrics_snapshot() -> dict[str, Any]:
    return registry.snapshot()


__all__ = [
    "MetricsRegistry",
    "metrics_snapshot",
    "record_agent_run",
    "record_http_request",
    "registry",
]
