"""
app/agent/logger.py

Logging utilities for the CRM Copilot AI Agent.

Responsibilities
----------------
- Log graph execution lifecycle
- Log retrieval events
- Log generation events
- Log graph failures

This module intentionally contains no business logic.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.observability.request_context import build_log_extra

logger = logging.getLogger("crm_copilot.agent")


class AgentLogger:
    """Helper for structured AI Agent logging."""

    @staticmethod
    def _log(level: int, message: str, **fields: object) -> None:
        logger.log(level, message, extra=build_log_extra(**fields))

    @staticmethod
    def graph_started(
        *,
        conversation_id: UUID,
        query: str,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.graph.started",
            conversation_id=str(conversation_id),
            query=query,
        )

    @staticmethod
    def graph_finished(
        *,
        conversation_id: UUID,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.graph.finished",
            conversation_id=str(conversation_id),
        )

    @staticmethod
    def retrieval_started(
        *,
        conversation_id: UUID,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.retrieval.started",
            conversation_id=str(conversation_id),
        )

    @staticmethod
    def retrieval_finished(
        *,
        conversation_id: UUID,
        document_count: int,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.retrieval.finished",
            conversation_id=str(conversation_id),
            document_count=document_count,
        )

    @staticmethod
    def generation_started(
        *,
        conversation_id: UUID,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.generation.started",
            conversation_id=str(conversation_id),
        )

    @staticmethod
    def generation_finished(
        *,
        conversation_id: UUID,
    ) -> None:
        AgentLogger._log(
            logging.INFO,
            "agent.generation.finished",
            conversation_id=str(conversation_id),
        )

    @staticmethod
    def graph_failed(
        *,
        conversation_id: UUID,
        error: Exception,
    ) -> None:
        logger.exception(
            "agent.graph.failed",
            extra=build_log_extra(
                conversation_id=str(conversation_id),
                error=type(error).__name__,
            ),
        )
