from __future__ import annotations

from types import SimpleNamespace

from packages.database.models.message import MessageRole

from app.services.llm.prompt_builder import PromptBuilder


# ---------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------


def test_build_system_prompt_default():
    prompt = PromptBuilder.build_system_prompt()

    assert "CRM Copilot" in prompt
    assert "AI assistant" in prompt
    assert len(prompt) > 0


def test_build_system_prompt_custom_name():
    prompt = PromptBuilder.build_system_prompt(
        assistant_name="Sales AI",
    )

    assert "Sales AI" in prompt
    assert "CRM Copilot" not in prompt


def test_build_system_prompt_additional_instructions():
    prompt = PromptBuilder.build_system_prompt(
        additional_instructions="Always answer in JSON.",
    )

    assert "Always answer in JSON." in prompt


# ---------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------


def test_build_with_empty_history():
    messages = PromptBuilder.build(
        system_prompt="System Prompt",
        history=[],
        user_message="Hello",
    )

    assert len(messages) == 2

    assert messages[0] == {
        "role": "system",
        "content": "System Prompt",
    }

    assert messages[1] == {
        "role": "user",
        "content": "Hello",
    }


def test_build_with_history():
    history = [
        SimpleNamespace(
            role=MessageRole.USER,
            content="Hi",
        ),
        SimpleNamespace(
            role=MessageRole.ASSISTANT,
            content="Hello!",
        ),
    ]

    messages = PromptBuilder.build(
        system_prompt="System",
        history=history,
        user_message="How are you?",
    )

    assert len(messages) == 4

    assert messages[0]["role"] == "system"

    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hi"

    assert messages[2]["role"] == "assistant"
    assert messages[2]["content"] == "Hello!"

    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "How are you?"


def test_build_with_context():
    messages = PromptBuilder.build(
        system_prompt="System",
        history=[],
        user_message="Question",
        context=[
            "CRM document",
            "Company policy",
        ],
    )

    assert len(messages) == 3

    assert messages[1]["role"] == "system"

    assert "CRM document" in messages[1]["content"]
    assert "Company policy" in messages[1]["content"]


def test_build_skips_empty_history_messages():
    history = [
        SimpleNamespace(
            role=MessageRole.USER,
            content="",
        ),
        SimpleNamespace(
            role=MessageRole.ASSISTANT,
            content=None,
        ),
        SimpleNamespace(
            role=MessageRole.USER,
            content="Real message",
        ),
    ]

    messages = PromptBuilder.build(
        system_prompt="System",
        history=history,
        user_message="Latest",
    )

    assert len(messages) == 3

    assert messages[1]["content"] == "Real message"

    assert messages[2]["content"] == "Latest"


# ---------------------------------------------------------------------
# _extract_role()
# ---------------------------------------------------------------------


def test_extract_role_from_enum():
    message = SimpleNamespace(
        role=MessageRole.USER,
        content="Hello",
    )

    assert PromptBuilder._extract_role(message) == "user"


def test_extract_role_from_string():
    message = SimpleNamespace(
        role="assistant",
        content="Hello",
    )

    assert PromptBuilder._extract_role(message) == "assistant"


def test_extract_role_from_dict():
    message = {
        "role": "system",
        "content": "Prompt",
    }

    assert PromptBuilder._extract_role(message) == "system"


def test_extract_role_default():
    message = SimpleNamespace(
        content="Hello",
    )

    assert PromptBuilder._extract_role(message) == "user"


# ---------------------------------------------------------------------
# _extract_content()
# ---------------------------------------------------------------------


def test_extract_content_from_model():
    message = SimpleNamespace(
        role=MessageRole.USER,
        content="Hello World",
    )

    assert PromptBuilder._extract_content(message) == "Hello World"


def test_extract_content_from_dict():
    message = {
        "role": "assistant",
        "content": "Hi",
    }

    assert PromptBuilder._extract_content(message) == "Hi"


def test_extract_content_none():
    message = SimpleNamespace(
        role=MessageRole.USER,
        content=None,
    )

    assert PromptBuilder._extract_content(message) == ""


def test_extract_content_missing():
    message = {}

    assert PromptBuilder._extract_content(message) == ""