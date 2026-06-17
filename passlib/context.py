"""Stub of ``passlib.context.CryptContext`` used in the project.

The real ``passlib`` library provides secure bcrypt hashing. For unit tests we
only need a deterministic, reversible (for verification) implementation that
behaves like ``hash`` and ``verify``. This stub uses ``hashlib.sha256`` to
produce a hex digest and stores the algorithm identifier ``bcrypt`` in the
result so that ``verify`` can detect mismatches.
"""

import hashlib


class CryptContext:
    """Very small stub mimicking the subset of ``passlib.context.CryptContext``.

    The constructor accepts ``schemes`` and ``deprecated`` arguments but ignores
    them – they exist only for API compatibility.
    """

    def __init__(self, schemes=None, deprecated=None):
        self.schemes = schemes or []
        self.deprecated = deprecated

    def hash(self, password: str) -> str:
        # Produce a deterministic "bcrypt"‑style string. Real bcrypt includes a
        # salt; here we use SHA‑256 for simplicity.
        digest = hashlib.sha256(password.encode()).hexdigest()
        return f"bcrypt${digest}"

    def verify(self, password: str, hashed: str) -> bool:
        # Expected format ``bcrypt$<hex>`` – verify by recomputing.
        try:
            prefix, stored = hashed.split("$", 1)
        except ValueError:
            return False
        if prefix != "bcrypt":
            return False
        return self.hash(password) == hashed
