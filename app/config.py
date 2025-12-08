"""
Configuration management using Pydantic Settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/auth_db"

    # Security
    SECRET_KEY: str = (
        "dev-secret-key-change-in-production-must-be-at-least-32-characters-long"
    )
    ALGORITHM: str = "HS256"

    # JWT Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # API Key Configuration
    API_KEY_EXPIRE_DAYS: int = 365

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # Paystack Configuration
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
