"""Integration tests for the security pipeline (requires GCP)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import requires_gcp


@requires_gcp
@pytest.mark.integration
class TestSecurityPipelineIntegration:
    """These tests call actual Model Armor APIs."""

    @pytest.mark.asyncio
    async def test_placeholder(self) -> None:
        """Placeholder — will be implemented when GCP env is ready."""
        pytest.skip("Integration test placeholder")
