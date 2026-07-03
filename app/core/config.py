"""Application configuration loaded from environment variables.

The module defines a ``Settings`` Pydantic model that loads all configuration
variables at runtime.  Individual constants are also exported for backward
compatibility with existing code that expects module-level names.
"""

import os
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings for the CRM Copilot application.

    Using a ``BaseSettings`` subclass provides automatic parsing of environment
    variables and convenient defaults for development/test environments.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          
    )

    # Core auth settings
    JWT_SECRET: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "test-secret"))
    ACCESS_TOKEN_EXPIRE_SECONDS: int = Field(default=900, env="ACCESS_TOKEN_EXPIRE_SECONDS")
    REFRESH_TOKEN_TTL_SECONDS: int = Field(default=2592000, env="REFRESH_TOKEN_TTL_SECONDS")
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    TOKEN_ALGORITHM: str = Field(default="HS256", env="TOKEN_ALGORITHM")
    JWT_ISSUER: str = Field(default="crm-copilot", env="JWT_ISSUER")
    JWT_AUDIENCE: str = Field(default="crm-copilot-api", env="JWT_AUDIENCE")

    # OpenAI provider configuration
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_TIMEOUT: float = Field(default=60.0, env="OPENAI_TIMEOUT")
    OPENAI_MAX_RETRIES: int = Field(default=3, env="OPENAI_MAX_RETRIES")


# Instantiate a single Settings object for module‑level constants.
_settings = Settings()

# Backward‑compatible constants – existing modules import these directly.
JWT_SECRET: Final[str] = _settings.JWT_SECRET
ACCESS_TOKEN_EXPIRE_SECONDS: Final[int] = _settings.ACCESS_TOKEN_EXPIRE_SECONDS
REFRESH_TOKEN_TTL_SECONDS: Final[int] = _settings.REFRESH_TOKEN_TTL_SECONDS
REDIS_URL: Final[str] = _settings.REDIS_URL
TOKEN_ALGORITHM: Final[str] = _settings.TOKEN_ALGORITHM
JWT_ISSUER: Final[str] = _settings.JWT_ISSUER
JWT_AUDIENCE: Final[str] = _settings.JWT_AUDIENCE

OPENAI_API_KEY: Final[str] = _settings.OPENAI_API_KEY
OPENAI_MODEL: Final[str] = _settings.OPENAI_MODEL
OPENAI_TIMEOUT: Final[float] = _settings.OPENAI_TIMEOUT
OPENAI_MAX_RETRIES: Final[int] = _settings.OPENAI_MAX_RETRIES


_settings = Settings()


def get_settings() -> Settings:
    """
    Return the singleton application settings.

    Using a singleton prevents re-reading the environment every time
    a dependency requests the configuration.
    """
    return _settings

__all__ = [
    "Settings",
    "get_settings",
    "JWT_SECRET",
    "ACCESS_TOKEN_EXPIRE_SECONDS",
    "REFRESH_TOKEN_TTL_SECONDS",
    "REDIS_URL",
    "TOKEN_ALGORITHM",
    "JWT_ISSUER",
    "JWT_AUDIENCE",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_TIMEOUT",
    "OPENAI_MAX_RETRIES",
]