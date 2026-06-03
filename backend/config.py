from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Required — fail fast if missing
    JWT_SECRET_KEY: str

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY muss mindestens 32 Zeichen lang sein")
        if "change-in-production" in v:
            raise ValueError("JWT_SECRET_KEY enthaelt unsicheren Standardwert — bitte aendern")
        return v
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Database
    DATABASE_URL: str = "sqlite:////app/appdata/speech1.db"
    USER_DATABASE_URL: str = "sqlite:////app/appdata/users.db"

    # Encryption (fallback: JWT_SECRET_KEY)
    ENCRYPTION_KEY: Optional[str] = None

    # CORS
    FRONTEND_URL: str = ""

    # App metadata
    APP_NAME: str = "PARK_SPEECH"
    APP_VERSION: str = "3.0.0"
    BUILD_DATE: str = "2025-07-31"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/appdata/logs"
    LOG_RETENTION_DAYS: int = 30
    LOG_CLEANUP_ENABLED: bool = True

    # Debug mode
    DEBUG: bool = False

    # Dev autologin button on login page
    DEV_AUTOLOGIN: bool = True

    # Test user credentials (created on startup when set + DEV_AUTOLOGIN=true)
    TEST_USERNAME: Optional[str] = None
    TEST_PASSWORD: Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
