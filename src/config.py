"""Application configuration from environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/leadiagent"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Ollama (override via OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS)
    ollama_base_url: str = "http://ollama:11434"
    ollama_timeout_seconds: int = 180
    ollama_model: str = "llama3"

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_addr: str = "noreply@example.com"
    smtp_from_email: str = "noreply@example.com"
    smtp_use_tls: bool = True
    enable_email: bool = False

    # Slack
    slack_webhook_url: str = ""
    enable_slack: bool = False

    # Scoring
    score_threshold_notify: int = 70  # Send email/Slack when score >= this

    # Logging
    log_level: str = "INFO"


settings = Settings()
