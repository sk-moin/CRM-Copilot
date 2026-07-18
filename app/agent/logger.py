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

logger = logging.getLogger("crm_copilot.agent")


class AgentLogger:
    """
    Helper for structured AI Agent logging.
    """

    @staticmethod
    def graph_started(
        *,
        conversation_id: UUID,
        query: str,
    ) -> None:
        logger.info(
            "Graph execution started | conversation_id=%s | query=%s",
            conversation_id,
            query,
        )

    @staticmethod
    def graph_finished(
        *,
        conversation_id: UUID,
    ) -> None:
        logger.info(
            "Graph execution finished | conversation_id=%s",
            conversation_id,
        )

    @staticmethod
    def retrieval_started(
        *,
        conversation_id: UUID,
    ) -> None:
        logger.info(
            "Retrieval started | conversation_id=%s",
            conversation_id,
        )

    @staticmethod
    def retrieval_finished(
        *,
        conversation_id: UUID,
        document_count: int,
    ) -> None:
        logger.info(
            (
                "Retrieval finished | "
                "conversation_id=%s | documents=%d"
            ),
            conversation_id,
            document_count,
        )

    @staticmethod
    def generation_started(
        *,
        conversation_id: UUID,
    ) -> None:
        logger.info(
            "Generation started | conversation_id=%s",
            conversation_id,
        )

    @staticmethod
    def generation_finished(
        *,
        conversation_id: UUID,
    ) -> None:
        logger.info(
            "Generation finished | conversation_id=%s",
            conversation_id,
        )

    @staticmethod
    def graph_failed(
        *,
        conversation_id: UUID,
        error: Exception,
    ) -> None:
        logger.exception(
            "Graph execution failed | conversation_id=%s",
            conversation_id,
            exc_info=error,
        )