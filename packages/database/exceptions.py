"""Shared database exceptions.

This module provides low-level exceptions used by the repository layer
and other database utilities. These are intentionally kept separate from
application-level exceptions to maintain clean separation of concerns.
"""

class DatabaseError(Exception):
    """Base class for all database-related exceptions."""
    pass


class InvalidTenantIdError(DatabaseError):
    """Raised when a tenant-scoped repository receives an invalid tenant_id.

    This guardrail prevents accidental data leakage across tenants by
    ensuring that tenant-scoped repositories always have a valid tenant_id.
    """
    pass