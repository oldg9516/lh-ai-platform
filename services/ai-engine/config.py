"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM APIs
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Database (Supabase REST API)
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index: str = "support-examples"
    pinecone_dimension: int = 1024  # text-embedding-3-large

    # Langfuse (Observability)
    langfuse_public_key: str = "pk-lf-local"
    langfuse_secret_key: str = "sk-lf-local"
    langfuse_host: str = "http://langfuse-web:3000"

    # Encryption
    cancel_link_password: str = ""

    # Chatwoot (Omnichannel)
    chatwoot_url: str = ""
    chatwoot_api_token: str = ""
    chatwoot_account_id: int = 1

    # App
    debug: bool = False
    log_level: str = "INFO"
    app_version: str = "0.1.0"


settings = Settings()
