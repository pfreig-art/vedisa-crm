from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://vedisa:password@localhost:5432/vedisa_crm"

    # Auth
    SECRET_KEY: str = "changeme"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM Providers
    OPENAI_API_KEY: str = ""
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_FALLBACK_MODEL: str = "claude-3-haiku-20240307"

    GEMINI_API_KEY: str = ""
    GEMINI_DEFAULT_MODEL: str = "gemini-1.5-pro"
    GEMINI_FALLBACK_MODEL: str = "gemini-1.5-flash"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_DEFAULT_MODEL: str = "deepseek-chat"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "anthropic/claude-3.5-sonnet"

    LITELLM_BASE_URL: str = "http://localhost:4000"
    LITELLM_API_KEY: str = ""
    LITELLM_DEFAULT_MODEL: str = ""

    # LLM Router
    LLM_PRIMARY_PROVIDER: str = "anthropic"
    LLM_FALLBACK_PROVIDER: str = "openai"
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 2

    # Observability
    OTEL_ENABLED: bool = False
    OTEL_ENDPOINT: str = "http://localhost:4318"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
