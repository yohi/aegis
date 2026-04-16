"""Tests for new validation logic and middleware robustness."""

from __future__ import annotations

import os

from core.config import AppConfig, SecurityConfig
from plugins.security.middleware import ModelArmorMiddleware


def test_security_config_allows_empty_project_id_for_initialization() -> None:
    """SecurityConfig should allow empty gcp_project_id for flexible initialization."""
    config = SecurityConfig(gcp_project_id="")
    assert config.gcp_project_id == ""


def test_app_config_env_prefix_change() -> None:
    """AppConfig should pick up security settings with the new LLM_SECURITY_ prefix."""
    os.environ["LLM_SECURITY_GCP_PROJECT_ID"] = "test-project-from-env"
    os.environ["LLM_SECURITY_LOCATION"] = "asia-northeast1"
    try:
        config = AppConfig()
        assert config.security.gcp_project_id == "test-project-from-env"
        assert config.security.location == "asia-northeast1"
    finally:
        del os.environ["LLM_SECURITY_GCP_PROJECT_ID"]
        del os.environ["LLM_SECURITY_LOCATION"]


class FakeResponse:
    """Generic fake for API response."""

    def __init__(self, **kwargs: object) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeFilterResult:
    """Fake for filter_results entry."""

    def __init__(self, match_state: str) -> None:
        self.match_state = match_state


def test_extract_findings_fallback_to_sanitization_result() -> None:
    """_extract_findings should check sanitization_result if findings is empty."""
    middleware = ModelArmorMiddleware(client=None)  # type: ignore

    # Case: findings is empty, but sanitization_result has matches
    response = FakeResponse(
        findings=[],
        sanitization_result=FakeResponse(
            filter_results={"pii_filter": FakeFilterResult("MATCH")}
        ),
    )

    findings = middleware._extract_findings(response)
    assert len(findings) == 1
    assert findings[0].category == "pii_filter"
    assert findings[0].severity == "high"


def test_extract_findings_prioritizes_findings_list() -> None:
    """_extract_findings should return findings list if it's not empty."""
    middleware = ModelArmorMiddleware(client=None)  # type: ignore

    response = FakeResponse(
        findings=[{"category": "test", "severity": "medium", "description": "desc"}],
        sanitization_result=FakeResponse(filter_results={"other": FakeFilterResult("MATCH")}),
    )

    findings = middleware._extract_findings(response)
    assert len(findings) == 1
    assert findings[0].category == "test"
    assert findings[0].severity == "medium"
