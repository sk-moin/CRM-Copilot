# Feature: Observability

**From build-plan:** feature 013
**Build attempt:** 1
**Branch:** feature/observability
**Status:** verified

## Goal

Add the observability layer for this service without introducing a heavy external stack: request-scoped structured logging, simple in-memory metrics, and agent/API trace metadata that make debugging and incident review straightforward. The feature augments the existing retrieval tracing from Spec 006 instead of replacing it.

## Design reference

None. This is a repository-native implementation that keeps the existing LangSmith integration and adds lightweight, local observability built with the Python standard library and the app's existing FastAPI/LangGraph stack.

## In scope

- Request-scoped logging with a stable request id attached to every log line
- Structured API access logs for method, path, status, duration, tenant, and user metadata
- In-memory metrics counters for HTTP requests, status codes, and agent executions
- A metrics endpoint that exposes the current counters for operators and tests
- Agent-side logging that includes the conversation, tenant, and org context
- Safe compatibility with the existing LangSmith retriever tracing and current app startup flow

## Out of scope

- Full OpenTelemetry instrumentation with exporters, Grafana, or Prometheus scraping
- Distributed tracing across external infrastructure or browser telemetry
- New external dependencies or cloud-specific observability vendors
- Deep alerting rules or dashboards beyond the basic metric snapshot

## Build loop

- [x] 1. Add structured API request logging and request context propagation for the FastAPI app
- [x] 2. Expose lightweight in-memory HTTP and agent metrics and make them queryable
- [x] 3. Wire agent logging to include the same request and conversation context and verify the behavior with targeted tests

## Build steps

- [x] 1. Implement request-scoped logging and context propagation for the API layer
  - Done when: every request emits a structured log line with `request_id`, `method`, `path`, `status_code`, `duration_ms`, `tenant_id`, and `org_id` when available, and the same request id is available to downstream log calls.
- [x] 2. Add in-memory metrics counters for API traffic and agent execution
  - Done when: a metrics snapshot exposes request totals by method/path/status and agent execution totals with latency, and the data updates during requests or direct API calls.
- [x] 3. Upgrade agent logging to use the same observability context and validate via tests
  - Done when: targeted pytest checks confirm the context helper and metric tracking behave as expected, and the app boots without changing the existing health and route behavior.

## Files / areas

- `app/main.py`
- `app/agent/logger.py`
- `app/observability/*.py`
- `tests/unit/observability/`

## Data / contracts

- Request id is generated once per incoming request and propagated through a context variable.
- Structured logs use a single flat key/value shape instead of ad hoc string interpolation.
- Metrics are kept in memory for local observability and exposed via `GET /metrics` in JSON form.
- LangSmith tracing remains opt-in via the existing `LANGSMITH_TRACING` configuration and does not become mandatory for this feature.

## Testing

- `python -m pytest tests/unit/observability/test_metrics.py`
- `python -m pytest tests/unit/observability/test_langsmith_tracing.py`
- Existing route and agent tests that touch the startup path continue to pass without changes.

## Notes for the AI

- Use the Python standard library for logging and metrics unless an existing repo pattern already requires a different tool.
- Keep the implementation lightweight and reversible; no new dependencies should be needed.
- Preserve the current startup and health-check behavior while adding request metadata and metrics.
- Do not broaden the feature into the full OpenTelemetry stack or production-grade dashboards; this is the lighter observability slice for V1.

## Open questions

None.
