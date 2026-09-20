"""Parse a CRM action proposal out of the agent's answer.

The provider interface has no `tools` parameter and the graph has no
tool-executor node, so this reads a fenced JSON block the model was asked to
emit rather than using native function calling. That is a deliberate, recorded
limitation of feature 010; native tool calling belongs with build-plan item
023.

Two rules govern this node:

- It never blocks a turn. A malformed, absent, or unsupported proposal leaves
  the answer exactly as generated. A user asking an ordinary question must not
  see an error because the model emitted something odd.
- It never mutates the CRM. It records a PENDING row and nothing else. The
  human decides.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.agent.state import AgentState
from app.observability.tracing import traced

logger = logging.getLogger(__name__)

# ```action
# { "action_type": "...", "payload": {...}, "reason": "..." }
# ```
_PROPOSAL_BLOCK = re.compile(
    r"```action\s*(?P<body>\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)

# Body-agnostic: matches an action fence whether or not its JSON parses, so a
# malformed block is removed from the answer rather than shown to the user.
_ANY_PROPOSAL_FENCE = re.compile(
    r"```action" + r"\b" + r".*?```",
    re.DOTALL | re.IGNORECASE,
)

_BLOCK_ONLY_REPLY = (
    "I have a suggested change for you to review, but could not describe it. "
    "Please check the pending actions list."
)


def extract_proposal(text: Optional[str]) -> Optional[dict[str, Any]]:
    """Return the proposal in `text`, or None.

    Returns None rather than raising for anything unparseable: at this point a
    bad proposal is the model's mistake, not the user's, and it must not cost
    them their answer.
    """

    if not text:
        return None

    match = _PROPOSAL_BLOCK.search(text)

    if match is None:
        return None

    try:
        parsed = json.loads(match.group("body"))
    except json.JSONDecodeError:
        logger.debug("agent.propose.unparseable_block")
        return None

    if not isinstance(parsed, dict):
        return None

    if not parsed.get("action_type"):
        return None

    return parsed


def strip_proposal(text: Optional[str]) -> Optional[str]:
    """Remove the proposal block so the user does not see raw JSON.

    `count=1` because the pattern is DOTALL: a global substitution over an
    unterminated action fence followed by any later fence would swallow
    everything between them.

    If stripping leaves nothing — the model replied with the block and no
    prose — the original text is returned. An empty answer would otherwise be
    streamed and persisted as the assistant message.
    """

    if not text:
        return text

    # Global, and on the fence pattern rather than the parsed body: a block
    # whose JSON is malformed still must not reach the user, and malformed
    # JSON is the commonest way a model gets this wrong. A second block is
    # stripped too.
    stripped = _ANY_PROPOSAL_FENCE.sub("", text).strip()

    # A reply that was nothing but the block would otherwise become an empty
    # assistant message, streamed and persisted.
    return stripped or _BLOCK_ONLY_REPLY


@traced(
    name="propose-node",
    run_type="chain",
    tags=["agent", "propose"],
)
async def propose_node(
    state: AgentState,
    *,
    action_service_factory: Any = None,
) -> AgentState:
    """Record any proposed action as PENDING.

    `action_service_factory` is injected by the graph builder so this node can
    stay unaware of request scope. When it is absent the node is inert, which
    keeps the graph usable in contexts with no session.
    """

    state.setdefault("proposed_action_id", None)

    # Extraction reads the block; stripping removes it. Keep the original so
    # the order of those two operations does not matter.
    state["_raw_response"] = state.get("response")

    # Strip whenever a fence is present, parsed or not. The block is
    # machine-readable plumbing: a malformed one, a second one, or a
    # deployment with no factory must all still keep it away from the user.
    if _ANY_PROPOSAL_FENCE.search(state.get("response") or ""):
        state["response"] = strip_proposal(state.get("response"))

    proposal = extract_proposal(state.get("response"))

    if proposal is None:
        # The block may have parsed before stripping; re-read the original.
        proposal = extract_proposal(state.get("_raw_response"))

    if proposal is None or action_service_factory is None:
        return state

    try:
        service = action_service_factory()

        action = await service.propose(
            action_type=str(proposal.get("action_type")),
            payload=proposal.get("payload") or {},
            reason=proposal.get("reason"),
            conversation_id=state.get("conversation_id"),
        )

        state["proposed_action_id"] = action.id

    except Exception:
        # A refused or broken proposal is logged and dropped. The turn stands.
        logger.warning("agent.propose.rejected", exc_info=True)

        state.setdefault("errors", []).append(
            {"node": "propose", "error": "proposal_rejected"}
        )

    return state
