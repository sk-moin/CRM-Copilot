"""Very small stub mimicking ``python-jose.jwt`` API.

Only the functions used by the project are implemented:
* ``encode(payload, key, algorithm)`` – returns a JSON string that includes the
  payload plus a ``_sig`` field. The signature is not cryptographically secure –
  it is merely a deterministic hash so that ``decode`` can retrieve the payload.
* ``decode(token, key, algorithms)`` – parses the token created by ``encode``
  and returns the original payload dictionary. If the token does not contain a
  ``_payload`` field, a ``JWTError`` is raised.

This stub is deliberately tiny and has no external dependencies, which is
acceptable for unit‑test isolation.
"""

import json
import hashlib
from typing import Any, Dict, List

from . import JWTError


def _sign(data: str, key: str) -> str:
    # Deterministic but insecure signature – just a SHA‑256 hash.
    return hashlib.sha256((data + key).encode()).hexdigest()


def encode(payload: Dict[str, Any], key: str, algorithm: str = "HS256") -> str:
    # Serialize payload as JSON and attach a simple signature.
    payload_json = json.dumps(payload, separators=(",", ":"))
    sig = _sign(payload_json, key)
    token_dict = {"_payload": payload, "_sig": sig}
    return json.dumps(token_dict)


def decode(token: str,key: str,algorithms: List[str],audience: str | None = None,issuer: str | None = None,options: Dict[str, Any] | None = None,) -> Dict[str, Any]:
    try:
        data = json.loads(token)
        payload = data["_payload"]
        sig = data["_sig"]
    except Exception as exc:
        raise JWTError("Invalid token format") from exc


    expected_sig = _sign(
        json.dumps(payload, separators=(",", ":")),
        key,
    )

    if sig != expected_sig:
        raise JWTError("Signature verification failed")

    options = options or {}

    verify_aud = options.get("verify_aud", True)
    verify_iss = options.get("verify_iss", True)

    if verify_aud and audience is not None:
        if payload.get("aud") != audience:
            raise JWTError("Invalid audience")

    if verify_iss and issuer is not None:
        if payload.get("iss") != issuer:
            raise JWTError("Invalid issuer")

    return payload


