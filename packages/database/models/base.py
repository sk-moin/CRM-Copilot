"""SQLAlchemy declarative base for the CRM project.

All ORM models inherit from this ``Base``.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
