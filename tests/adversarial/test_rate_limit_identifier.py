"""Adversarial tests for the rate-limit identifier.

A bucket key a caller can influence is a rate limiter a caller can defeat:
pick your own key and you pick your own budget. Two properties matter here,
matching the tenant-isolation convention this file sits beside:

* Two distinct principals -- even in the same tenant -- must never land in
  the same bucket, or one user's traffic throttles another's.
* A caller must never be able to choose their own bucket by forging a
  header, or the whole feature becomes decorative.
"""

from __future__ import annotations

import pytest
from starlette.requests import Request

from app.api.rate_limit import _auth_identifier, _client_address, _identifier
from app.core import config
from app.core.security import create_access_token


def _request(*, headers: list[tuple[bytes, bytes]] | None = None, client=("1.2.3.4", 1)):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/probe",
        "headers": headers or [],
        "client": client,
        "query_string": b"",
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


def _bearer(token: str, **kwargs):
    return _request(headers=[(b"authorization", f"Bearer {token}".encode())], **kwargs)


def _token(*, user_id: str, tenant_id: str) -> str:
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        org_id="org-doesnt-matter-here",
        email=f"{user_id}@example.com",
        role="OWNER",
    )


@pytest.mark.asyncio
async def test_two_users_in_one_tenant_get_separate_buckets():
    tenant = "tenant-shared"

    token_a = _token(user_id="user-a", tenant_id=tenant)
    token_b = _token(user_id="user-b", tenant_id=tenant)

    identity_a = await _identifier(_bearer(token_a))
    identity_b = await _identifier(_bearer(token_b))

    assert identity_a != identity_b
    assert identity_a == "tenant:tenant-shared:user:user-a"
    assert identity_b == "tenant:tenant-shared:user:user-b"


@pytest.mark.asyncio
async def test_two_tenants_do_not_collide_even_with_the_same_user_id():
    """The tenant is part of the key, not just the user.

    If it were not, a UUID collision -- or, worse, a deliberately chosen
    user id -- could let one tenant's traffic count against another's.
    """

    token_a = _token(user_id="same-user-id", tenant_id="tenant-a")
    token_b = _token(user_id="same-user-id", tenant_id="tenant-b")

    identity_a = await _identifier(_bearer(token_a))
    identity_b = await _identifier(_bearer(token_b))

    assert identity_a != identity_b


@pytest.mark.asyncio
async def test_auth_bucket_uses_client_address_even_with_a_valid_bearer_token():
    token = _token(user_id="user-a", tenant_id="tenant-a")
    request = _bearer(
        token,
        client=("203.0.113.9", 1),
    )

    assert await _identifier(request) == "tenant:tenant-a:user:user-a"
    assert await _auth_identifier(request) == "ip:203.0.113.9"


@pytest.mark.asyncio
async def test_a_forged_token_cannot_pick_an_arbitrary_bucket():
    """A JWT with the right shape but the wrong signature must not decode.

    Otherwise anyone could forge a `sub`/`tenant_id` pair naming a busy
    victim's bucket, or manufacture an endless supply of fresh ones to avoid
    ever being caught by any bucket at all.
    """

    forged = create_access_token(
        user_id="victim-user",
        tenant_id="victim-tenant",
        org_id="org",
        email="victim@example.com",
        role="OWNER",
    )
    # Change a significant signature character. The final base64url character
    # can contain unused bits, so changing it may decode to the same bytes.
    header_and_payload, _, signature = forged.rpartition(".")
    tampered_signature = f"{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
    tampered = f"{header_and_payload}.{tampered_signature}"

    identity = await _identifier(_bearer(tampered, client=("198.51.100.20", 1)))

    # Falls back to the IP bucket, not to the forged tenant/user claims.
    assert identity == "ip:198.51.100.20"
    assert "victim" not in identity


@pytest.mark.asyncio
async def test_a_caller_cannot_choose_their_own_bucket_via_forwarded_for(
    monkeypatch,
):
    """The one place a purely anonymous caller could try to pick a key."""

    monkeypatch.setattr(config, "TRUSTED_PROXY_COUNT", 0)

    real_client = ("203.0.113.9", 1)

    honest = await _identifier(_request(client=real_client))
    forged = await _identifier(
        _request(
            headers=[(b"x-forwarded-for", b"someone-elses-bucket")],
            client=real_client,
        )
    )

    assert honest == forged == "ip:203.0.113.9"


@pytest.mark.asyncio
async def test_the_client_address_helper_agrees_with_the_identifier():
    """Redundant with the identifier tests above, on purpose.

    `_identifier` is what production actually calls; this pins the same
    property directly against `_client_address`, the function that would
    need to change if the spoofing protection ever regressed there
    specifically rather than in how `_identifier` calls it.
    """

    assert _client_address(
        _request(
            headers=[(b"x-forwarded-for", b"1.1.1.1")],
            client=("203.0.113.9", 1),
        )
    ) == "203.0.113.9"
