"""Unit tests for the local observability metrics and request context."""

from __future__ import annotations

from app.observability.metrics import MetricsRegistry
from app.observability.request_context import current_request_id, request_context


def test_request_context_tracks_values() -> None:
    with request_context(
        request_id="req-123",
        tenant_id="tenant-456",
        org_id="org-789",
        user_id="user-100",
    ):
        assert current_request_id() == "req-123"

    assert current_request_id() is None


def test_metrics_registry_tracks_http_and_agent_runs() -> None:
    registry = MetricsRegistry()

    registry.record_http_request(
        method="POST",
        path="/api/v1/chat",
        status_code=201,
        duration_ms=12.5,
    )
    registry.record_http_request(
        method="POST",
        path="/api/v1/chat",
        status_code=200,
        duration_ms=8.1,
    )
    registry.record_agent_run(
        name="crm-agent",
        duration_ms=42.0,
        success=True,
    )
    registry.record_agent_run(
        name="crm-agent",
        duration_ms=15.0,
        success=False,
    )

    snapshot = registry.snapshot()

    assert snapshot["http_requests"]["POST:/api/v1/chat:201"] == 1
    assert snapshot["http_requests"]["POST:/api/v1/chat:200"] == 1
    assert snapshot["http_status_codes"]["201"] == 1
    assert snapshot["agent_runs"]["crm-agent"] == 2
    assert snapshot["agent_failures"]["crm-agent"] == 1
    assert snapshot["request_latency_ms"]["count"] == 2
