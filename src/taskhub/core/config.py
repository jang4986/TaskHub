from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "TaskHub — Hệ thống quản lý công việc (Task Management API)"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskhub.db"

    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # Security & JWT (Loaded strictly from environment / .env without hardcoded default)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7


settings = Settings()
