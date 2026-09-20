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
    OPENAI_BASE_URL: str | None = Field(default=None, env="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    OPENAI_TIMEOUT: float = Field(default=60.0, env="OPENAI_TIMEOUT")
    OPENAI_MAX_RETRIES: int = Field(default=3, env="OPENAI_MAX_RETRIES")

    # OpenRouter provider configuration
    OPENROUTER_API_KEY: str | None = Field(default=None, env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="openai/gpt-oss-20b:free", env="OPENROUTER_MODEL")

    GROQ_API_KEY: str | None = Field(default=None, env="GROQ_API_KEY")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b", env="GROQ_MODEL")

    LLM_PROVIDER: str = Field(default="openrouter", env="LLM_PROVIDER")

    HF_TOKEN: str | None = Field(default=None,env="HF_TOKEN")
        
    APP_URL: str = Field(default="http://localhost:8000",env="APP_URL")


    LANGSMITH_API_KEY: str | None = Field(default=None, env="LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = Field(default="crm-copilot", env="LANGSMITH_PROJECT")
    LANGSMITH_TRACING: bool = Field(default=False, env="LANGSMITH_TRACING")

    ENVIRONMENT: str = "development"

    EMBEDDING_PROVIDER: str = Field(default="huggingface", env="EMBEDDING_PROVIDER")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")

    GUARDRAILS_ENABLED: bool = True
    GUARDRAILS_CONFIG_PATH: str = "app/guardrails/rails"
    GUARDRAILS_PROVIDER: str = "nemo"
    GUARDRAILS_VERBOSE: bool = False


    GUARDRAIL_INPUT_ENABLED: bool = True
    GUARDRAIL_JAILBREAK_ENABLED: bool = True
    GUARDRAIL_PROMPT_INJECTION_ENABLED: bool = True
    GUARDRAIL_INPUT_FALLBACK_MESSAGE: str = ("I'm sorry, but I can't assist with that request.")

    GUARDRAIL_OUTPUT_ENABLED: bool = True
    GUARDRAIL_OUTPUT_BLOCK_ON_VIOLATION: bool = True
    GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR: bool = True
    GUARDRAIL_OUTPUT_MAX_RESPONSE_LENGTH: int = 12000
    GUARDRAIL_OUTPUT_FALLBACK_MESSAGE: str = (
        "I'm sorry, but I can't provide that response. "
        "Please try rephrasing your request."
    )
    GUARDRAIL_OUTPUT_CHECK_PROMPT_LEAKAGE: bool = True
    GUARDRAIL_OUTPUT_CHECK_UNSAFE_CONTENT: bool = True
    GUARDRAIL_OUTPUT_CHECK_RESPONSE_QUALITY: bool = True

    


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

OPENROUTER_API_KEY: str | None = _settings.OPENROUTER_API_KEY
OPENROUTER_MODEL: str = _settings.OPENROUTER_MODEL
GROQ_API_KEY: str | None = _settings.GROQ_API_KEY
GROQ_MODEL: str = _settings.GROQ_MODEL

LANGSMITH_API_KEY: str = _settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT: str = _settings.LANGSMITH_PROJECT
LANGSMITH_TRACING: bool = _settings.LANGSMITH_TRACING

EMBEDDING_PROVIDER: str = _settings.EMBEDDING_PROVIDER
EMBEDDING_MODEL: str = _settings.EMBEDDING_MODEL

GUARDRAILS_ENABLED: bool = _settings.GUARDRAILS_ENABLED
GUARDRAILS_CONFIG_PATH: str = _settings.GUARDRAILS_CONFIG_PATH
GUARDRAILS_PROVIDER: str = _settings.GUARDRAILS_PROVIDER
GUARDRAILS_VERBOSE: bool = _settings.GUARDRAILS_VERBOSE

HF_TOKEN: str | None = _settings.HF_TOKEN

LLM_PROVIDER: str = _settings.LLM_PROVIDER

APP_URL: str = _settings.APP_URL

ENVIRONMENT: str = _settings.ENVIRONMENT

GUARDRAIL_INPUT_ENABLED: bool = _settings.GUARDRAIL_INPUT_ENABLED
GUARDRAIL_JAILBREAK_ENABLED: bool = _settings.GUARDRAIL_JAILBREAK_ENABLED
GUARDRAIL_PROMPT_INJECTION_ENABLED: bool = _settings.GUARDRAIL_PROMPT_INJECTION_ENABLED
GUARDRAIL_INPUT_FALLBACK_MESSAGE: str = _settings.GUARDRAIL_INPUT_FALLBACK_MESSAGE

GUARDRAIL_OUTPUT_ENABLED: bool = _settings.GUARDRAIL_OUTPUT_ENABLED
GUARDRAIL_OUTPUT_BLOCK_ON_VIOLATION: bool = _settings.GUARDRAIL_OUTPUT_BLOCK_ON_VIOLATION
GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR: bool = _settings.GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR
GUARDRAIL_OUTPUT_MAX_RESPONSE_LENGTH: int = _settings.GUARDRAIL_OUTPUT_MAX_RESPONSE_LENGTH
GUARDRAIL_OUTPUT_FALLBACK_MESSAGE: str = _settings.GUARDRAIL_OUTPUT_FALLBACK_MESSAGE
GUARDRAIL_OUTPUT_CHECK_PROMPT_LEAKAGE: bool = _settings.GUARDRAIL_OUTPUT_CHECK_PROMPT_LEAKAGE
GUARDRAIL_OUTPUT_CHECK_UNSAFE_CONTENT: bool = _settings.GUARDRAIL_OUTPUT_CHECK_UNSAFE_CONTENT
GUARDRAIL_OUTPUT_CHECK_RESPONSE_QUALITY: bool = _settings.GUARDRAIL_OUTPUT_CHECK_RESPONSE_QUALITY





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
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_TRACING",
    "APP_URL",
    "ENVIRONMENT",
    "LLM_PROVIDER",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL",
    "GUARDRAILS_ENABLED",
    "GUARDRAILS_CONFIG_PATH",
    "GUARDRAILS_PROVIDER",
    "GUARDRAILS_VERBOSE",
    "HF_TOKEN",
    "GUARDRAIL_INPUT_ENABLED",
    "GUARDRAIL_JAILBREAK_ENABLED",
    "GUARDRAIL_PROMPT_INJECTION_ENABLED",
    "GUARDRAIL_INPUT_FALLBACK_MESSAGE",
    "GUARDRAIL_OUTPUT_ENABLED",
    "GUARDRAIL_OUTPUT_BLOCK_ON_VIOLATION",
    "GUARDRAIL_OUTPUT_FAIL_CLOSED_ON_ERROR",
    "GUARDRAIL_OUTPUT_MAX_RESPONSE_LENGTH",
    "GUARDRAIL_OUTPUT_FALLBACK_MESSAGE",
    "GUARDRAIL_OUTPUT_CHECK_PROMPT_LEAKAGE",
    "GUARDRAIL_OUTPUT_CHECK_UNSAFE_CONTENT",
    "GUARDRAIL_OUTPUT_CHECK_RESPONSE_QUALITY",
]