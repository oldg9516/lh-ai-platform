"""Configuration for Dash Analytics Agent."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Dash service settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase read-only connection for customer data queries
    data_db_url: str = "postgresql+psycopg://analytics_readonly:analytics_pass@supabase-db:5432/postgres"

    # OpenAI
    openai_api_key: str = ""

    # Runtime
    runtime_env: str = "dev"
    log_level: str = "INFO"


settings = Settings()
