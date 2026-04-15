"""Integration tests for the sync pipeline (requires GCP)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import requires_gcp


@requires_gcp
@pytest.mark.integration
class TestSyncPipelineIntegration:
    """These tests call actual Google Drive / NotebookLM APIs."""

    @pytest.mark.asyncio
    async def test_placeholder(self) -> None:
        """Placeholder — will be implemented when GCP env is ready."""
        pytest.skip("Integration test placeholder")
