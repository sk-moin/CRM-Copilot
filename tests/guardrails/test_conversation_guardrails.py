from pathlib import Path

from nemoguardrails import RailsConfig


RAILS_PATH = Path("app/guardrails/rails")


def _load_config() -> RailsConfig:
    """Load the complete NeMo Guardrails configuration."""
    return RailsConfig.from_path(str(RAILS_PATH))


def test_greeting_flow_is_registered_as_dialog_rail() -> None:
    """Phase 3.1: greeting must be registered as a dialog rail."""

    config_path = RAILS_PATH / "config.yml"
    content = config_path.read_text(encoding="utf-8")

    assert "dialog:" in content
    assert "- greeting" in content

    config = _load_config()

    assert config is not None


def test_greeting_flow_defines_supported_greetings() -> None:
    """Phase 3.1: supported greeting intents must exist."""

    greeting_path = RAILS_PATH / "flows" / "greeting.co"
    content = greeting_path.read_text(encoding="utf-8").lower()

    expected_greetings = [
        '"hi"',
        '"hello"',
        '"hey"',
        '"good morning"',
        '"good afternoon"',
        '"good evening"',
    ]

    for greeting in expected_greetings:
        assert greeting in content


def test_greeting_flow_returns_crm_copilot_greeting() -> None:
    """Phase 3.1: greeting flow must define the CRM Copilot response."""

    greeting_path = RAILS_PATH / "flows" / "greeting.co"
    content = greeting_path.read_text(encoding="utf-8")

    assert "define flow greeting" in content
    assert "user express greeting" in content
    assert "bot express greeting" in content
    assert "Hello! How can I help you today?" in content


def test_refusal_flow_is_registered_as_dialog_rail() -> None:
    """Phase 3.2: refusal must be registered as a dialog rail."""

    config_path = RAILS_PATH / "config.yml"
    content = config_path.read_text(encoding="utf-8")

    assert "dialog:" in content
    assert "- refusal" in content

    config = _load_config()

    assert config is not None


def test_refusal_flow_is_defined() -> None:
    """Phase 3.2: refusal flow must exist and contain a bot response."""

    refusal_path = RAILS_PATH / "flows" / "refusal.co"

    assert refusal_path.exists()

    content = refusal_path.read_text(encoding="utf-8")

    assert "define flow refusal" in content
    assert "bot say" in content


def test_refusal_flow_returns_safe_response() -> None:
    """Phase 3.2: refusal flow must return the configured safe response."""

    refusal_path = RAILS_PATH / "flows" / "refusal.co"
    content = refusal_path.read_text(encoding="utf-8")

    assert (
        "I'm sorry, but I can't assist with that request."
        in content
    )

def test_off_topic_flow_is_registered_as_dialog_rail() -> None:
    """Phase 3.3: off-topic flow must be registered as a dialog rail."""

    config_path = RAILS_PATH / "config.yml"
    content = config_path.read_text(encoding="utf-8")

    assert "dialog:" in content
    assert "- off topic" in content

    config = _load_config()

    assert config is not None


def test_off_topic_flow_defines_supported_examples() -> None:
    """Phase 3.3: off-topic flow must contain representative examples."""

    off_topic_path = RAILS_PATH / "flows" / "off_topic.co"

    assert off_topic_path.exists()

    content = off_topic_path.read_text(
        encoding="utf-8"
    ).lower()

    expected_examples = [
        '"what\'s the weather today?"',
        '"who won the football match?"',
        '"tell me a joke"',
        '"recommend a movie"',
        '"help me with a python programming problem"',
        '"what\'s a good recipe for dinner?"',
    ]

    for example in expected_examples:
        assert example in content


def test_off_topic_flow_returns_crm_scope_response() -> None:
    """Phase 3.3: off-topic requests must receive the CRM scope response."""

    off_topic_path = RAILS_PATH / "flows" / "off_topic.co"

    content = off_topic_path.read_text(
        encoding="utf-8"
    )

    assert "define flow off topic" in content
    assert "user ask off topic" in content
    assert "bot respond off topic" in content
    assert "I'm focused on CRM-related tasks" in content

def test_identity_flow_is_registered_as_dialog_rail() -> None:
    """Phase 3.4: identity flow must be registered."""

    config_path = RAILS_PATH / "config.yml"
    content = config_path.read_text(encoding="utf-8")

    assert "dialog:" in content
    assert "- identity" in content

    config = _load_config()

    assert config is not None


def test_identity_protection_flow_is_registered() -> None:
    """Phase 3.4: identity protection flow must be registered."""

    config_path = RAILS_PATH / "config.yml"
    content = config_path.read_text(encoding="utf-8")

    assert "- identity protection" in content

    config = _load_config()

    assert config is not None


def test_identity_flow_defines_identity_questions() -> None:
    """Phase 3.4: identity questions must be explicitly defined."""

    identity_path = RAILS_PATH / "flows" / "identity.co"

    assert identity_path.exists()

    content = identity_path.read_text(
        encoding="utf-8"
    )

    expected_questions = [
        '"Who are you?"',
        '"What are you?"',
        '"What is your name?"',
        '"Are you an AI?"',
        '"Are you a human?"',
    ]

    for question in expected_questions:
        assert question in content


def test_identity_flow_returns_crm_copilot_identity() -> None:
    """Phase 3.4: identity questions must return CRM Copilot identity."""

    identity_path = RAILS_PATH / "flows" / "identity.co"

    content = identity_path.read_text(
        encoding="utf-8"
    )

    assert "define flow identity" in content
    assert "user ask identity" in content
    assert "bot respond identity" in content
    assert "I am CRM Copilot" in content


def test_identity_protection_flow_is_defined() -> None:
    """Phase 3.4: identity override attempts must be handled."""

    identity_path = RAILS_PATH / "flows" / "identity.co"

    content = identity_path.read_text(
        encoding="utf-8"
    )

    assert "define user challenge identity" in content
    assert "define flow identity protection" in content
    assert "bot protect identity" in content


def test_identity_protection_does_not_allow_identity_change() -> None:
    """
    Phase 3.4: identity override attempts must not cause the assistant
    to claim a different identity.
    """

    identity_path = RAILS_PATH / "flows" / "identity.co"

    content = identity_path.read_text(
        encoding="utf-8"
    )

    protected_response = (
        "I am CRM Copilot, an AI assistant for customer "
        "relationship management."
    )

    assert protected_response in content