"""The propose node: record proposals, never break a turn.

Two rules matter here. A proposal must become exactly one PENDING action, and
anything malformed must leave the user's answer untouched — a person asking an
ordinary question should never lose their reply because the model emitted
something strange.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.nodes.propose import (
    extract_proposal,
    propose_node,
    strip_proposal,
)

PROPOSAL = """Here is what I found, and I suggest a follow-up.

```action
{"action_type": "CREATE_TASK", "payload": {"title": "Call Acme"}, "reason": "You asked."}
```
"""


class RecordingService:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.fail = fail

    async def propose(self, **kwargs):
        if self.fail:
            raise ValueError("refused")

        self.calls.append(kwargs)

        class _Action:
            id = uuid4()

        return _Action()


def _state(response, conversation_id=None):
    return {
        "response": response,
        "conversation_id": conversation_id or uuid4(),
        "errors": [],
    }


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def test_extract_reads_a_well_formed_block():
    proposal = extract_proposal(PROPOSAL)

    assert proposal["action_type"] == "CREATE_TASK"
    assert proposal["payload"]["title"] == "Call Acme"


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "Just an ordinary answer with no proposal.",
        "```action\nnot json at all\n```",
        "```action\n[1, 2, 3]\n```",
        '```action\n{"payload": {}}\n```',  # no action_type
    ],
)
def test_extract_returns_none_for_anything_unusable(text):
    assert extract_proposal(text) is None


def test_strip_removes_the_machine_readable_block():
    stripped = strip_proposal(PROPOSAL)

    assert "```action" not in stripped
    assert "Here is what I found" in stripped


# --------------------------------------------------------------------------- #
# The node
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_a_proposal_creates_exactly_one_pending_action():
    service = RecordingService()
    conversation_id = uuid4()

    state = await propose_node(
        _state(PROPOSAL, conversation_id),
        action_service_factory=lambda: service,
    )

    assert len(service.calls) == 1
    assert service.calls[0]["action_type"] == "CREATE_TASK"
    assert service.calls[0]["conversation_id"] == conversation_id
    assert state["proposed_action_id"] is not None


@pytest.mark.asyncio
async def test_the_user_never_sees_the_raw_block():
    service = RecordingService()

    state = await propose_node(
        _state(PROPOSAL),
        action_service_factory=lambda: service,
    )

    assert "```action" not in state["response"]
    assert "Here is what I found" in state["response"]


@pytest.mark.asyncio
async def test_an_ordinary_answer_proposes_nothing():
    service = RecordingService()
    answer = "Acme has 3 open opportunities."

    state = await propose_node(
        _state(answer),
        action_service_factory=lambda: service,
    )

    assert service.calls == []
    assert state["proposed_action_id"] is None
    assert state["response"] == answer


@pytest.mark.asyncio
async def test_a_malformed_proposal_does_not_fail_the_turn():
    service = RecordingService()
    answer = "Here you go.\n```action\n{oops\n```"

    state = await propose_node(
        _state(answer),
        action_service_factory=lambda: service,
    )

    assert service.calls == []
    assert state["proposed_action_id"] is None

    # The turn survives, and the malformed block does not reach the user.
    # Truncated or invalid JSON is the commonest way a model gets this wrong,
    # so this is the likeliest path to a raw block in the conversation.
    assert state["response"]
    assert "```action" not in state["response"]
    assert "Here you go." in state["response"]


@pytest.mark.asyncio
async def test_a_refused_proposal_does_not_fail_the_turn():
    """A rejected payload is the model's problem, not the user's."""

    service = RecordingService(fail=True)

    state = await propose_node(
        _state(PROPOSAL),
        action_service_factory=lambda: service,
    )

    assert state["proposed_action_id"] is None
    assert state["response"]
    assert any(e["node"] == "propose" for e in state["errors"])


@pytest.mark.asyncio
async def test_the_node_is_inert_without_a_factory():
    """Keeps the graph usable where there is no request-scoped session."""

    state = await propose_node(_state(PROPOSAL), action_service_factory=None)

    assert state["proposed_action_id"] is None

    # The block is still stripped: it is plumbing, and a deployment without a
    # factory should not show users raw JSON.
    assert "```action" not in state["response"]
    assert "Here is what I found" in state["response"]


def test_strip_keeps_the_answer_when_the_block_is_all_there_is():
    """An empty answer would be streamed and persisted as the message."""

    only_block = chr(10).join(
        ["```action", '{"action_type": "CREATE_TASK", "payload": {}}', "```"]
    )

    stripped = strip_proposal(only_block)

    # Not the raw block, and not empty: an empty string would be streamed and
    # persisted as the assistant message.
    assert "```action" not in stripped
    assert stripped.strip()


def test_strip_does_not_swallow_content_between_unrelated_fences():
    """DOTALL with a global substitution would eat everything between them."""

    text = chr(10).join(
        [
            "Intro.",
            "```action",
            '{"action_type": "CREATE_TASK"}',
            "```",
            "Keep me.",
            "```python",
            "print(1)",
            "```",
        ]
    )

    stripped = strip_proposal(text)

    assert "Keep me." in stripped
    assert "print(1)" in stripped
