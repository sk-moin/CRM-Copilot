# Stub package for ``python-jose`` used in tests.
# Provides minimal ``jwt`` submodule with ``encode`` / ``decode`` functions
# and a ``JWTError`` exception. This is sufficient for the AuthService unit
# tests which only need to round‑trip a payload.

class JWTError(Exception):
    """Exception raised for JWT decode errors (stub)."""
    pass
