"""Integration tests for the security pipeline (requires GCP)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import requires_gcp


@requires_gcp
@pytest.mark.integration
class TestSecurityPipelineIntegration:
    """These tests call actual Model Armor APIs."""

    @pytest.mark.skip(reason="Integration test placeholder — implementation pending")
    async def test_placeholder(self) -> None:
        """Placeholder."""
        pass
