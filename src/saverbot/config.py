"""Configuration for saverbot using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    LOG_LEVEL: str = "INFO"


config = Config()
