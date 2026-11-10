from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "TaskHub — Hệ thống quản lý công việc (Task Management API)"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskhub.db"

    # Security & JWT
    SECRET_KEY: str = "your-super-secret-key-taskhub-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24


settings = Settings()
