"""Secrets must not survive into anything that renders the settings.

An independent review of feature 011 reproduced this: the suite's provider
pin was written `assert get_settings().LLM_PROVIDER == "mock"`, and when it
fired from conftest at module level pytest's assertion rewriting reported
`where <the whole Settings repr>.LLM_PROVIDER` -- printing a live JWT secret
into the failure message, and from there into a terminal scrollback, a pasted
traceback, or a public CI log.

Two layers are pinned here. The fields are excluded from `__repr__`, which
covers `repr()`, `str()`, f-strings and logging the object -- but not
`model_dump()`, `vars()` or a `ValidationError` on a secret field, which
`app/core/config.py` lists and a test below pins. The conftest pins also
compare two locals, which keeps the message short for any field.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.core.config import Settings, get_settings

CANARY = "canary-value-that-must-not-be-printed"


def _all_canary_settings() -> Settings:
    """Settings with every secret replaced.

    Setting only one leaves the rest loaded from the environment, so any
    test that renders the object discloses the others.
    """

    return Settings(**{field: CANARY for field in SECRET_FIELDS})


SECRET_FIELDS = (
    "JWT_SECRET",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "HF_TOKEN",
    "LANGSMITH_API_KEY",
)


def test_no_secret_field_appears_in_the_settings_repr():
    """Asserts on the list of offending names, never on the rendering.

    `assert field not in repr(get_settings())` would be the obvious way to
    write this and it is a trap: pytest renders the operands of a failed
    assertion, so the moment this test caught a regression it would print
    the live settings -- the exact disclosure it exists to prevent, into
    whatever log was being written at the time. Reduce to names first.
    """

    # Not bound to a local: `--showlocals` prints locals on failure, and a
    # local holding the live repr would disclose even though the assertion
    # itself does not.
    leaking = sorted(
        field for field in SECRET_FIELDS if field in repr(get_settings())
    )

    assert leaking == [], (
        f"these secret settings are rendered by Settings.__repr__: "
        f"{leaking}. Anything that prints the settings object discloses "
        "them. Add repr=False."
    )


def test_a_secret_value_does_not_survive_into_the_repr():
    """Not just the name: the value itself.

    Built explicitly rather than read from the environment, so the test does
    not depend on a populated .env, and every secret is replaced so nothing
    real is in the object at all. The assertions still reduce to booleans
    before comparing, because that is the layer that survives someone
    adding a seventh secret and forgetting the canary.
    """

    settings = _all_canary_settings()

    # Reduced to booleans before asserting, so a failure cannot render the
    # object. Every secret is a canary, so there is nothing real in it
    # either -- both layers, because one of them is easy to undo later.
    in_repr = CANARY in repr(settings)
    in_str = CANARY in str(settings)

    assert in_repr is False, "the canary survived into repr()"
    assert in_str is False, "the canary survived into str()"

    # Still reachable by the code that legitimately needs it.
    assert settings.JWT_SECRET == CANARY


def test_every_secret_looking_setting_is_excluded_from_the_repr():
    """Catches a new secret added later without `repr=False`.

    The list above is maintained by hand, so this walks the model instead and
    holds any field whose name looks like a credential to the same rule.
    """

    looks_secret = re.compile(r"(SECRET|PASSWORD|API_KEY|TOKEN)$")

    missing = [
        name
        for name, field in Settings.model_fields.items()
        if looks_secret.search(name) and field.repr
    ]

    assert missing == [], (
        f"these settings render in the repr and look like credentials: "
        f"{missing}. Add repr=False."
    )


def test_the_paths_repr_false_does_not_cover_are_recorded_not_assumed():
    """`repr=False` hides the repr, not the values.

    Pinned as current documented behaviour rather than as a defect: a
    settings object still discloses through `model_dump()` and friends,
    and the comment in `app/core/config.py` says exactly that. If someone
    later moves these to `SecretStr`, this test fails and points at the
    comment that has to change with it.

    Every secret is a canary here, not just one. Setting a single field
    left the other five loaded from the environment, so a failure rendered
    real credentials. Each assertion is also reduced to a bool first,
    because pytest renders the value of a call node -- and these calls
    return the dump itself.
    """

    settings = _all_canary_settings()

    in_dump = CANARY in settings.model_dump_json()
    in_vars = CANARY in str(vars(settings))
    dumped = settings.model_dump()["JWT_SECRET"] == CANARY

    assert in_dump is True, "model_dump_json no longer discloses; update the comment"
    assert in_vars is True, "vars() no longer discloses; update the comment"
    assert dumped is True, "model_dump no longer discloses; update the comment"


def test_the_conftest_provider_pins_compare_two_locals():
    """The second layer, and the one the review actually tripped over.

    A call on the left of `==` makes pytest render the receiver. `repr=False`
    already blanks the secrets, but keeping the pins bound to locals means a
    failure reports two short strings rather than the whole settings object.
    """

    source = Path(__file__).resolve().parents[2] / "conftest.py"

    # Code only: the comment there explains the hazard and naturally quotes
    # the shape it is warning about.
    text = chr(10).join(
        line
        for line in source.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )

    assert "assert get_settings()." not in text, (
        "tests/conftest.py asserts directly on a get_settings() call, so a "
        "failure renders the settings object; bind it to a local first"
    )
