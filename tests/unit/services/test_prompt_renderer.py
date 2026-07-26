"""
Tests for PromptRenderer.
"""

from __future__ import annotations

import pytest

from app.services.llm.prompt_renderer import PromptRenderer


@pytest.fixture
def renderer() -> PromptRenderer:
    """
    Return a PromptRenderer instance.
    """
    return PromptRenderer()


def test_render_simple_variable(
    renderer: PromptRenderer,
):
    """
    Renderer should substitute a single variable.
    """

    template = "Hello {{ name }}"

    rendered = renderer.render(
        template=template,
        variables={
            "name": "Alice",
        },
    )

    assert rendered == "Hello Alice"


def test_render_multiple_variables(
    renderer: PromptRenderer,
):
    """
    Renderer should substitute multiple variables.
    """

    template = (
        "{{ greeting }} {{ name }}!"
    )

    rendered = renderer.render(
        template=template,
        variables={
            "greeting": "Welcome",
            "name": "Bob",
        },
    )

    assert rendered == "Welcome Bob!"


def test_render_without_variables(
    renderer: PromptRenderer,
):
    """
    Static templates should render unchanged.
    """

    template = "CRM Copilot"

    rendered = renderer.render(
        template=template,
        variables={},
    )

    assert rendered == "CRM Copilot"


def test_missing_variable(
    renderer: PromptRenderer,
):
    """
    Missing variables should not raise errors.
    """

    template = "Hello {{ name }}"

    rendered = renderer.render(
        template=template,
        variables={},
    )

    assert isinstance(rendered, str)


def test_loop_rendering(
    renderer: PromptRenderer,
):
    """
    Jinja loops should render correctly.
    """

    template = """
{% for item in items %}
- {{ item }}
{% endfor %}
""".strip()

    rendered = renderer.render(
        template=template,
        variables={
            "items": [
                "Company",
                "Contact",
                "Opportunity",
            ],
        },
    )

    assert "- Company" in rendered
    assert "- Contact" in rendered
    assert "- Opportunity" in rendered


def test_if_statement(
    renderer: PromptRenderer,
):
    """
    Conditional blocks should render.
    """

    template = """
{% if admin %}
Admin
{% else %}
User
{% endif %}
""".strip()

    rendered = renderer.render(
        template=template,
        variables={
            "admin": True,
        },
    )

    assert "Admin" in rendered


def test_nested_variables(
    renderer: PromptRenderer,
):
    """
    Nested dictionaries should be supported.
    """

    template = (
        "{{ company.name }}"
    )

    rendered = renderer.render(
        template=template,
        variables={
            "company": {
                "name": "OpenAI",
            },
        },
    )

    assert rendered == "OpenAI"


def test_none_variables(
    renderer: PromptRenderer,
):
    """
    None values should not raise errors.
    """

    template = (
        "User: {{ user }}"
    )

    rendered = renderer.render(
        template=template,
        variables={
            "user": None,
        },
    )

    assert isinstance(rendered, str)


def test_empty_template(
    renderer: PromptRenderer,
):
    """
    Empty template should render to an empty string.
    """

    rendered = renderer.render(
        template="",
        variables={},
    )

    assert rendered == ""


def test_whitespace_preserved(
    renderer: PromptRenderer,
):
    """
    Renderer should preserve template whitespace.
    """

    template = "Hello\n\n{{ name }}"

    rendered = renderer.render(
        template=template,
        variables={
            "name": "CRM",
        },
    )

    assert rendered == "Hello\n\nCRM"