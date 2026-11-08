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


settings = Settings()
