"""Request-scoped observability context."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_request_id: ContextVar[str | None] = ContextVar("crm_request_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("crm_tenant_id", default=None)
_org_id: ContextVar[str | None] = ContextVar("crm_org_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("crm_user_id", default=None)


def current_request_id() -> str | None:
    return _request_id.get()


def current_tenant_id() -> str | None:
    return _tenant_id.get()


def current_org_id() -> str | None:
    return _org_id.get()


def current_user_id() -> str | None:
    return _user_id.get()


def build_log_extra(**extra: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "request_id": current_request_id(),
        "tenant_id": current_tenant_id(),
        "org_id": current_org_id(),
        "user_id": current_user_id(),
    }
    payload.update(extra)
    return {key: value for key, value in payload.items() if value is not None}


@contextmanager
def request_context(
    *,
    request_id: str | None = None,
    tenant_id: str | None = None,
    org_id: str | None = None,
    user_id: str | None = None,
) -> Iterator[None]:
    request_token = _request_id.set(request_id or str(uuid.uuid4()))
    tenant_token = _tenant_id.set(tenant_id)
    org_token = _org_id.set(org_id)
    user_token = _user_id.set(user_id)
    try:
        yield
    finally:
        _request_id.reset(request_token)
        _tenant_id.reset(tenant_token)
        _org_id.reset(org_token)
        _user_id.reset(user_token)


__all__ = [
    "build_log_extra",
    "current_org_id",
    "current_request_id",
    "current_tenant_id",
    "current_user_id",
    "request_context",
]
