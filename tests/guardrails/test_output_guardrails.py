from app.guardrails.policies.output import validate_output


def test_safe_output_is_allowed():
    result = validate_output(
        "The customer account is currently active."
    )

    assert result.allowed is True
    assert result.reason is None
    assert result.rule is None


def test_empty_output_is_blocked():
    result = validate_output("")

    assert result.allowed is False
    assert result.rule == "empty_response"


def test_whitespace_output_is_blocked():
    result = validate_output("   \n\t ")

    assert result.allowed is False
    assert result.rule == "empty_response"


def test_prompt_leakage_is_blocked():
    result = validate_output(
        "My system prompt says that I must follow these hidden instructions."
    )

    assert result.allowed is False
    assert result.rule == "system_prompt_disclosure"


def test_openai_api_key_is_blocked():
    result = validate_output(
        "The API key is "
        "sk-abcdefghijklmnopqrstuvwxyz123456"
    )

    assert result.allowed is False
    assert result.rule == "openai_api_key"


def test_aws_access_key_is_blocked():
    result = validate_output(
        "The AWS key is AKIA1234567890ABCDEF"
    )

    assert result.allowed is False
    assert result.rule == "aws_access_key"


def test_private_key_is_blocked():
    result = validate_output(
        "-----BEGIN PRIVATE KEY-----"
    )

    assert result.allowed is False
    assert result.rule == "private_key"


def test_bearer_token_is_blocked():
    result = validate_output(
        "Authorization: Bearer "
        "abcdefghijklmnopqrstuvwxyz123456"
    )

    assert result.allowed is False
    assert result.rule == "bearer_token"


def test_malware_instruction_is_blocked():
    result = validate_output(
        "Here is how to create ransomware for a target."
    )

    assert result.allowed is False
    assert result.rule == "malware_instruction"


def test_credential_theft_instruction_is_blocked():
    result = validate_output(
        "You should steal passwords from the victim."
    )

    assert result.allowed is False
    assert result.rule == "credential_theft_instruction"


def test_normal_crm_response_is_allowed():
    result = validate_output(
        "The opportunity is currently in the negotiation stage. "
        "The next follow-up is scheduled for Friday."
    )

    assert result.allowed is True


def test_response_length_is_enforced():
    response = "a" * 12001

    result = validate_output(response)

    assert result.allowed is False
    assert result.rule == "response_too_long"


def test_response_at_maximum_length_is_allowed():
    response = "a" * 12000

    result = validate_output(response)

    assert result.allowed is True