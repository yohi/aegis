"""Tests for new validation logic and middleware robustness."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.config import SecurityConfig
from plugins.security.middleware import ModelArmorMiddleware


def test_security_config_requires_project_id() -> None:
    """SecurityConfig should fail if gcp_project_id is empty or missing."""
    with pytest.raises(ValidationError):
        SecurityConfig(gcp_project_id="")


class FakeResponse:
    """Generic fake for API response."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeFilterResult:
    """Fake for filter_results entry."""
    def __init__(self, match_state: str):
        self.match_state = match_state


def test_extract_findings_fallback_to_sanitization_result() -> None:
    """_extract_findings should check sanitization_result if findings is empty."""
    middleware = ModelArmorMiddleware(client=None)  # type: ignore
    
    # Case: findings is empty, but sanitization_result has matches
    response = FakeResponse(
        findings=[],
        sanitization_result=FakeResponse(
            filter_results={
                "pii_filter": FakeFilterResult("MATCH")
            }
        )
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
        sanitization_result=FakeResponse(
            filter_results={
                "other": FakeFilterResult("MATCH")
            }
        )
    )
    
    findings = middleware._extract_findings(response)
    assert len(findings) == 1
    assert findings[0].category == "test"
    assert findings[0].severity == "medium"
