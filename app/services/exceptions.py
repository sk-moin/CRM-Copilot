"""Domain‑specific exceptions for the authentication service.

These exceptions are raised by ``AuthService`` and will be translated to HTTP
responses by the FastAPI router layer (e.g., ``DuplicateEmailError`` → 409).
"""


class AuthError(Exception):
    """Base class for all authentication‑related domain errors."""

    pass


class DuplicateEmailError(AuthError):
    """Raised when a registration attempt uses an email that already exists."""

    pass


class DuplicateSubdomainError(AuthError):
    """Raised when the supplied tenant subdomain already exists."""

    pass


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid (wrong email or password)."""

    pass


class UserNotFoundError(AuthError):
    """Raised when a user cannot be found by its primary key."""

    pass


class InvalidTenantIdError(AuthError):
    """Raised when a tenant-scoped repository receives an invalid tenant_id."""

    pass
