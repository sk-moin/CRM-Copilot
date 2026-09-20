# AI Guardrails

This module provides the integration between CRM Copilot and **NVIDIA NeMo Guardrails**.

## Responsibilities

- Initialize NeMo Guardrails.
- Validate AI requests.
- Validate AI responses.
- Execute conversation rails.
- Provide a single abstraction for the rest of the application.

## Design Principles

- Business logic must never interact with NeMo directly.
- All integrations must go through `GuardrailService`.
- Future guardrail providers can be added without affecting the application.

## Structure

```
guardrails/
│
├── config.py
├── service.py
├── dependencies.py
├── exceptions.py
│
├── providers/
│
└── rails/
```

This module is introduced in **Spec 009 – AI Guardrails & Safety**.