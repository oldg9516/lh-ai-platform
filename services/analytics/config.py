"""Configuration for Analytics Service."""

from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Analytics service settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (PostgreSQL read-only connection)
    analytics_db_url: str = "postgresql://analytics_readonly:analytics_pass@localhost:5432/postgres"

    # OpenAI (for analytics agent)
    openai_api_key: str

    # Pinecone (for knowledge base)
    pinecone_api_key: str
    pinecone_index: str = "support-examples"

    # Langfuse (observability - separate project from ai-engine)
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"

    # Service
    debug: bool = False
    log_level: str = "INFO"

    # Parsed DB components (for PostgresTools which doesn't accept db_url directly)
    @property
    def db_host(self) -> str:
        """Extract host from analytics_db_url."""
        parsed = urlparse(self.analytics_db_url)
        return parsed.hostname or "localhost"

    @property
    def db_port(self) -> int:
        """Extract port from analytics_db_url."""
        parsed = urlparse(self.analytics_db_url)
        return parsed.port or 5432

    @property
    def db_name(self) -> str:
        """Extract database name from analytics_db_url."""
        parsed = urlparse(self.analytics_db_url)
        return parsed.path.lstrip("/") or "postgres"

    @property
    def db_user(self) -> str:
        """Extract username from analytics_db_url."""
        parsed = urlparse(self.analytics_db_url)
        return parsed.username or "postgres"

    @property
    def db_password(self) -> str:
        """Extract password from analytics_db_url."""
        parsed = urlparse(self.analytics_db_url)
        return parsed.password or ""

    @property
    def sqlalchemy_db_url(self) -> str:
        """DB URL with psycopg driver for SQLAlchemy (used by PgVector)."""
        # Replace postgresql:// with postgresql+psycopg:// to use psycopg3 instead of psycopg2
        return self.analytics_db_url.replace("postgresql://", "postgresql+psycopg://")


settings = Settings()
