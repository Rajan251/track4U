import json
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:8000"]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # JWT
    JWT_SECRET: str = "super-secret-jwt-key-change-in-production-123456789"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_FROM_EMAIL: str = ""

    # Custom global alert recipients (always receive every alert email)
    # Comma-separated in .env: ALERT_TO_EMAILS=a@b.com,c@d.com
    ALERT_TO_EMAILS: Union[List[str], str] = []

    # Expiry Tracker Settings
    ALERT_THRESHOLD_DAYS: int = 30
    # De-duplication window: skip re-sending same alert within this many hours
    EMAIL_ALERT_DEDUP_HOURS: int = 11

    # Scheduler cron times (UTC)
    # Default: 02:30 UTC = 8:00 AM IST, 14:30 UTC = 8:00 PM IST
    SCHEDULER_HOUR_1: int = 2
    SCHEDULER_MINUTE_1: int = 30
    SCHEDULER_HOUR_2: int = 14
    SCHEDULER_MINUTE_2: int = 30

    # Internal API security token
    INTERNAL_API_TOKEN: str = "internal-secret-token-change-in-production"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [i.strip() for i in v.split(",")]
        return v

    @field_validator("ALERT_TO_EMAILS", mode="before")
    @classmethod
    def parse_alert_emails(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return [e.strip() for e in v if e.strip()]
        if isinstance(v, str):
            if not v.strip():
                return []
            if v.startswith("[") and v.endswith("]"):
                return json.loads(v)
            return [e.strip() for e in v.split(",") if e.strip()]
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
