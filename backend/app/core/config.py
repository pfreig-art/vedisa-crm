"""Application settings loaded from environment / .env.

Compatibilidad: se conservan los nombres en mayusculas usados previamente
(DATABASE_URL, SECRET_KEY, etc.) y se exponen alias en minusculas
(database_url, jwt_secret, ...) requeridos por el bloque A del Sprint D.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database (valor por defecto: SQLite local para dev sin .env)
    DATABASE_URL: str = "sqlite+aiosqlite:///./vedisa_dev.db"

    # Auth / JWT
    SECRET_KEY: str = "changeme-dev-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Runtime
    ENVIRONMENT: str = "production"
    HOST: str = "127.0.0.1"
    PORT: int = 8081
    APP_VERSION: str = "0.3.0"

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

    # ---- Alias en minusculas requeridos por Sprint D bloque A ----
    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def jwt_secret(self) -> str:
        return self.SECRET_KEY

    @property
    def jwt_algorithm(self) -> str:
        return self.ALGORITHM

    @property
    def jwt_expires_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def cors_origins(self) -> List[str]:
        return self.CORS_ORIGINS

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    @property
    def host(self) -> str:
        return self.HOST

    @property
    def port(self) -> int:
        return self.PORT

    @property
    def app_version(self) -> str:
        return self.APP_VERSION


settings = Settings()
