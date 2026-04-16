"""Configuration management using Pydantic Settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SyncConfig(BaseSettings):
    """Configuration for Google Drive / NotebookLM sync."""

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

    model_config = SettingsConfigDict(env_prefix="LLM_SECURITY_")

    # Keep default empty to allow AppConfig() without arguments.
    # Validation should be performed before actual API use.
    gcp_project_id: str = ""
    location: str = "us-central1"

    model_armor_template_id: str = "default-shield"
    block_on_high_severity: bool = True
    log_findings: bool = True


class RetryConfig(BaseSettings):
    """Configuration for transient error retries."""

    model_config = SettingsConfigDict(env_prefix="LLM_REVIEW_RETRY_")

    max_attempts: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 60.0
    retryable_exceptions: list[str] = Field(
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
