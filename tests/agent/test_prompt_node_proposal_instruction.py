"""Every tenant must be told how to propose a CRM change.

`prompt_node` prefers a prompt from the feature-008 store and falls back to the
built-in one. The proposal instruction originally lived only in the fallback,
so any org with its own stored `crm_chat` prompt never learned the syntax, the
model never emitted a proposal block, and the whole approval layer was silently
inert for that tenant — with no error and no log line.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.nodes.prompt import prompt_node


class StubPromptManager:
    """Returns a stored prompt, or None to force the built-in fallback."""

    def __init__(self, stored: str | None) -> None:
        self.stored = stored

    async def render_prompt(self, **kwargs) -> str | None:
        return self.stored


class CapturingBuilder:
    def __init__(self) -> None:
        self.system_prompt: str | None = None

    def build(self, *, system_prompt, query, messages, documents) -> str:
        self.system_prompt = system_prompt
        return "built"


def _state():
    return {
        "org_id": uuid4(),
        "query": "Remind me to call Acme",
        "messages": [],
        "retrieved_documents": [],
    }


async def _system_prompt_for(stored: str | None) -> str:
    builder = CapturingBuilder()

    await prompt_node(
        _state(),
        prompt_builder=builder,
        prompt_manager=StubPromptManager(stored),
    )

    return builder.system_prompt


@pytest.mark.asyncio
async def test_a_tenant_with_a_stored_prompt_still_learns_to_propose():
    """The case that was broken: the org has its own prompt."""

    prompt = await _system_prompt_for("You are a bespoke assistant for Acme.")

    assert "You are a bespoke assistant for Acme." in prompt
    assert "```action" in prompt
    assert "CREATE_TASK" in prompt


@pytest.mark.asyncio
async def test_the_builtin_fallback_also_carries_it():
    prompt = await _system_prompt_for(None)

    assert "```action" in prompt
    assert "CREATE_TASK" in prompt


@pytest.mark.asyncio
async def test_the_instruction_is_not_duplicated():
    """A stored prompt that already explains the block must not get a second
    copy."""

    from app.agent.prompts.system_prompt import ACTION_PROPOSAL_INSTRUCTION

    prompt = await _system_prompt_for(
        "Custom preamble.\n\n" + ACTION_PROPOSAL_INSTRUCTION
    )

    assert prompt.count("Should the assistant response be blocked") == 0
    assert prompt.count("CREATE_TASK, UPDATE_TASK_STATUS") == 1
