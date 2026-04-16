"""Tests for plugins/sync/drive_client.py."""

from __future__ import annotations

from plugins.sync.drive_client import DriveClient
from tests.unit.conftest import FakeDriveClient


class TestDriveClient:
    """Verify Protocol definitions exist and are runtime_checkable."""

    def test_drive_client_is_runtime_checkable(self) -> None:
        assert isinstance(FakeDriveClient(), DriveClient)
