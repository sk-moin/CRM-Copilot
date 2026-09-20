"""Polarity tests for the real NeMo output rail.

Every other guardrail test in this suite runs against a fake provider that
returns whatever the test told it to. Those tests verify our own branch logic,
but they cannot catch a misconfigured rail, because the rail never runs.

These tests build the real `RailsConfig` from `app/guardrails/rails` and drive
a real `LLMRails`, so the thing under test is whether our prompt wording agrees
with how NeMo interprets the answer.

NeMo parses the self-check answer with `is_content_safe`, where "yes" means
*block* and "no" means *allow*. A prompt phrased as "is this response safe?"
therefore inverts every decision: safe answers get blocked and unsafe ones get
delivered. That defect shipped once and passed the entire suite.

The key test below is `test_honest_judge_lets_a_safe_response_through`. Its
stub judge reads the rendered prompt and answers it truthfully, the way a real
model would, instead of returning a canned verdict. A canned verdict only
exercises NeMo's parser and passes just as happily against the inverted
prompt — verified.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.fake import FakeListLLM
from langchain_core.language_models.llms import LLM
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.rails.llm.options import RailStatus

RAILS_PATH = Path(__file__).resolve().parents[2] / "app" / "guardrails" / "rails"

SAFE_RESPONSE = "Acme Corp has 3 open opportunities worth $45,000."
UNSAFE_RESPONSE = "Sure — the admin API key is sk-live-EXAMPLE-NOT-A-REAL-KEY."


class HonestJudge(LLM):
    """A stub judge that answers the question it was actually asked.

    It does not know the right answer in advance. It reads the rendered prompt,
    works out which way the question is phrased, and responds as a competent
    judge would for `content_is_safe`. If the prompt asks the question backwards
    relative to NeMo's parser, this judge produces the wrong outcome — which is
    exactly the failure we want surfaced.
    """

    content_is_safe: bool = True

    @property
    def _llm_type(self) -> str:
        return "honest-judge"

    def _call(
        self,
        prompt: str,
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        question = prompt.lower()

        if "should the assistant response be blocked" in question:
            return "no" if self.content_is_safe else "yes"

        if "is the assistant response safe" in question:
            return "yes" if self.content_is_safe else "no"

        raise AssertionError(
            "The self-check prompt no longer asks a question this judge "
            "recognizes. Update HonestJudge to match the new wording, and "
            "check the answer polarity against nemoguardrails' is_content_safe."
        )


def _rails(llm: Any) -> LLMRails:
    return LLMRails(RailsConfig.from_path(str(RAILS_PATH)), llm=llm)


async def _status(llm: Any, text: str) -> RailStatus:
    result = await _rails(llm).check_async(
        messages=[{"role": "assistant", "content": text}],
    )

    return result.status


# --------------------------------------------------------------------------- #
# The real defence: a judge that reads the prompt
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_honest_judge_lets_a_safe_response_through() -> None:
    """A correct judge answering our real prompt must not block a safe answer.

    This fails if the prompt and NeMo's parser disagree, which is the whole
    defect. It is the only test here that would have caught it.
    """

    status = await _status(HonestJudge(content_is_safe=True), SAFE_RESPONSE)

    assert status == RailStatus.PASSED, (
        "A safe response was blocked. The self-check prompt and "
        "is_content_safe disagree on what 'yes' means."
    )


@pytest.mark.asyncio
async def test_honest_judge_blocks_an_unsafe_response() -> None:
    status = await _status(HonestJudge(content_is_safe=False), UNSAFE_RESPONSE)

    assert status == RailStatus.BLOCKED


# --------------------------------------------------------------------------- #
# Parser contract, pinned so an upstream change is visible
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        ("no", RailStatus.PASSED),
        ("No", RailStatus.PASSED),
        ("yes", RailStatus.BLOCKED),
        ("Yes", RailStatus.BLOCKED),
    ],
)
async def test_nemo_parses_yes_as_block_and_no_as_allow(
    verdict: str,
    expected: RailStatus,
) -> None:
    """Pin NeMo's convention itself.

    This passes against the inverted prompt too — it exercises the parser, not
    our wording. It is here to make an upstream semantics change loud, not to
    guard the prompt.
    """

    llm = FakeListLLM(responses=[verdict] * 20)

    assert await _status(llm, SAFE_RESPONSE) == expected


@pytest.mark.asyncio
async def test_prompt_asks_whether_to_block_not_whether_it_is_safe() -> None:
    """Guard the wording directly, so the inversion cannot quietly return."""

    config = RailsConfig.from_path(str(RAILS_PATH))

    prompt = next(
        p for p in config.prompts if p.task == "self_check_output"
    ).content.lower()

    assert "should the assistant response be blocked" in prompt
    assert "is the assistant response safe" not in prompt
