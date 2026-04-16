"""Integration test configuration.

Integration tests call actual GCP APIs and require credentials.
Skip automatically when credentials are not available.
"""

from __future__ import annotations

import os

import pytest

requires_gcp = pytest.mark.skipif(
    not os.environ.get("LLM_REVIEW_SECURITY_GCP_PROJECT_ID", "").strip(),
    reason="GCP credentials not configured (set LLM_REVIEW_SECURITY_GCP_PROJECT_ID)",
)
