"""
LangSmith configuration.

Centralized configuration for LangSmith observability.

Responsibilities
----------------
- Configure LangSmith environment
- Create a shared LangSmith client
- Enable/disable tracing
- Provide helper functions for observability

Notes
-----
This module should be the only place in the project that knows how
LangSmith is configured. Other modules should import helpers from here
instead of directly interacting with environment variables.
"""

from __future__ import annotations

import os

from langsmith import Client


def is_tracing_enabled() -> bool:
    """
    Return whether LangSmith tracing is enabled.

    Returns
    -------
    bool
        True when tracing is enabled.
    """
    return os.getenv(
        "LANGSMITH_TRACING",
        "false",
    ).lower() == "true"


def get_project_name() -> str:
    """
    Return the configured LangSmith project name.

    Returns
    -------
    str
        LangSmith project.
    """
    return os.getenv(
        "LANGSMITH_PROJECT",
        "crm-copilot",
    )


from app.core.config import get_settings

def get_client() -> Client:
    settings = get_settings()

    return Client(
        api_key=settings.LANGSMITH_API_KEY,
        api_url="https://api.smith.langchain.com",
    )


__all__ = [
    "get_client",
    "get_project_name",
    "is_tracing_enabled",
]