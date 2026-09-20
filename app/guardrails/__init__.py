"""
AI Guardrails module.

This package provides the integration layer between the application
and NVIDIA NeMo Guardrails.

Business logic should never interact with NeMo directly. Instead,
all guardrail operations should go through the GuardrailService.
"""

from app.guardrails.service import GuardrailService

__all__ = ["GuardrailService"]