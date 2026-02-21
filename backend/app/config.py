"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    anthropic_api_key: str
    stripe_secret_key: str
    stripe_webhook_secret: str = ""
    supabase_url: str
    supabase_key: str
    jwt_secret: str = "dev-secret"

    class Config:
        env_file = ".env"


settings = Settings()
