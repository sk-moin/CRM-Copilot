"""
Trace metadata helpers.

Utilities for constructing standardized metadata attached to LangSmith
traces throughout CRM Copilot.

Responsibilities
----------------
- Build tenant metadata
- Build organization metadata
- Build conversation metadata
- Build user metadata
- Merge metadata dictionaries

Notes
-----
All LangSmith traces should use these helpers to ensure consistent
metadata across the application.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID


def tenant_metadata(
    tenant_id: UUID | str,
) -> dict[str, str]:
    """
    Build tenant metadata.

    Parameters
    ----------
    tenant_id:
        Tenant identifier.

    Returns
    -------
    dict[str, str]
    """
    return {
        "tenant_id": str(tenant_id),
    }


def organization_metadata(
    org_id: UUID | str,
) -> dict[str, str]:
    """
    Build organization metadata.

    Parameters
    ----------
    org_id:
        Organization identifier.

    Returns
    -------
    dict[str, str]
    """
    return {
        "org_id": str(org_id),
    }


def conversation_metadata(
    conversation_id: UUID | str,
) -> dict[str, str]:
    """
    Build conversation metadata.

    Parameters
    ----------
    conversation_id:
        Conversation identifier.

    Returns
    -------
    dict[str, str]
    """
    return {
        "conversation_id": str(conversation_id),
    }


def user_metadata(
    user_id: UUID | str,
) -> dict[str, str]:
    """
    Build user metadata.

    Parameters
    ----------
    user_id:
        User identifier.

    Returns
    -------
    dict[str, str]
    """
    return {
        "user_id": str(user_id),
    }


def build_metadata(
    *,
    tenant_id: UUID | str,
    org_id: UUID | str,
    conversation_id: UUID | str | None = None,
    user_id: UUID | str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build standard CRM metadata for LangSmith traces.

    Parameters
    ----------
    tenant_id:
        Tenant identifier.

    org_id:
        Organization identifier.

    conversation_id:
        Conversation identifier.

    user_id:
        User identifier.

    extra:
        Additional metadata to include.

    Returns
    -------
    dict[str, Any]
    """
    metadata: dict[str, Any] = {}

    metadata.update(
        tenant_metadata(tenant_id),
    )

    metadata.update(
        organization_metadata(org_id),
    )

    if conversation_id is not None:
        metadata.update(
            conversation_metadata(conversation_id),
        )

    if user_id is not None:
        metadata.update(
            user_metadata(user_id),
        )

    if extra:
        metadata.update(extra)

    return metadata


__all__ = [
    "tenant_metadata",
    "organization_metadata",
    "conversation_metadata",
    "user_metadata",
    "build_metadata",
]