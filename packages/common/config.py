"""Typed application configuration using Pydantic Settings."""
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    TIMEZONE: str = Field(default="Asia/Kolkata", description="System timezone")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/india_market_terminal",
        description="Async PostgreSQL connection URL",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/india_market_terminal",
        description="Sync PostgreSQL connection URL for migrations",
    )
    DB_POOL_SIZE: int = Field(default=10, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")

    # API Server
    API_HOST: str = Field(default="0.0.0.0", description="API bind host")
    API_PORT: int = Field(default=8000, description="API bind port")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )

    # Document & Cache Storage
    STORAGE_DIR: Path = Field(
        default=BASE_DIR / "data" / "documents",
        description="Local directory for storing ingested documents (PDFs, raw HTML)",
    )

    # AI Framework Configuration (Framework only, no local models)
    AI_ACTIVE_PROVIDER: str = Field(default="rule_fallback", description="Active AI provider: rule_fallback, gemini, openai_compatible")
    AI_FALLBACK_PROVIDER: str = Field(default="rule_fallback", description="Fallback AI provider")
    AI_CACHE_ENABLED: bool = Field(default=True, description="Whether to cache AI outputs in Postgres")
    AI_CACHE_TTL_DAYS: int = Field(default=7, description="AI cache time-to-live in days")
    
    # Pluggable API Keys (will be populated when specified by user)
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-flash-lite-latest", description="Gemini model name")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI or compatible API Key")
    OPENAI_BASE_URL: Optional[str] = Field(default=None, description="OpenAI compatible base URL")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model name")

    # Telegram Alert Bot (Optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = Field(default=None, description="Telegram Bot API Token")
    TELEGRAM_CHAT_ID: Optional[str] = Field(default=None, description="Default Telegram Chat ID for alerts")

    # Market Data & Broker Adapter Mesh
    MARKET_DATA_PRIMARY: str = Field(default="free", description="Primary market data provider: free, upstox, mock")
    MARKET_DATA_FALLBACK: str = Field(default="free", description="Fallback market data provider")
    UPSTOX_ENABLED: bool = Field(default=False, description="Enable Upstox integration as an optional authenticated provider")
    UPSTOX_CLIENT_ID: Optional[str] = Field(default=None, description="Upstox API Client ID / Key")
    UPSTOX_CLIENT_SECRET: Optional[str] = Field(default=None, description="Upstox API Client Secret")
    UPSTOX_ACCESS_TOKEN: Optional[str] = Field(default=None, description="Upstox OAuth Access Token")
    UPSTOX_REDIRECT_URI: str = Field(default="http://localhost:8000/market/upstox/callback", description="Upstox OAuth Callback URI")

    # Polling & Collector Defaults
    COLLECTOR_USER_AGENT: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        description="User-Agent header for public exchange scraping",
    )
    COLLECTOR_TIMEOUT_SECONDS: int = Field(default=15, description="Default request timeout")
    COLLECTOR_MAX_RETRIES: int = Field(default=3, description="Default request retries")


settings = Settings()

