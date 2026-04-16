"""Integration tests for the sync pipeline (requires GCP)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import requires_gcp


@requires_gcp
@pytest.mark.integration
class TestSyncPipelineIntegration:
    """These tests call actual Google Drive / NotebookLM APIs."""

    @pytest.mark.skip(reason="Integration test placeholder — implementation pending")
    async def test_placeholder(self) -> None:
        """Placeholder."""
        pass
