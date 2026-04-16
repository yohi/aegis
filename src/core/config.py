"""Configuration classes using pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncConfig(BaseSettings):
    """Configuration for the sync pipeline."""

    model_config = SettingsConfigDict(env_prefix="LLM_REVIEW_SYNC_")

    notebook_id: str = ""
    drive_folder_id: str = ""
    file_patterns: list[str] = Field(default_factory=lambda: ["**/*.py", "**/*.ts", "**/*.tsx"])
    exclude_patterns: list[str] = Field(
        default_factory=lambda: ["**/node_modules/**", "**/.venv/**"]
    )
    max_file_size_kb: int = 500


class SecurityConfig(BaseSettings):
    """Configuration for Model Armor security."""

    model_config = SettingsConfigDict(env_prefix="LLM_REVIEW_SECURITY_")

    gcp_project_id: str = ""
    model_armor_location: str = "us-central1"
    model_armor_template_id: str = "default-shield"
    block_on_high_severity: bool = True
    log_findings: bool = True


class RetryConfig(BaseSettings):
    """Configuration for retry behavior."""

    model_config = SettingsConfigDict(env_prefix="LLM_REVIEW_RETRY_")

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    retryable_errors: list[str] = Field(
        default_factory=lambda: [
            "google.api_core.exceptions.ServiceUnavailable",
            "google.api_core.exceptions.DeadlineExceeded",
        ]
    )


class AppConfig(BaseSettings):
    """Top-level application configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_REVIEW_")

    sync: SyncConfig = Field(default_factory=SyncConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
