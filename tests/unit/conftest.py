"""Shared test fixtures and fake implementations."""

from __future__ import annotations

from pathlib import Path

from core.types import (
    ShieldResult,
    SyncResult,
)


class FakeDriveClient:
    """Test DriveClient (Protocol-compliant)."""

    def __init__(self) -> None:
        self.uploaded_files: list[tuple[Path, str]] = []
        self.synced_notebooks: list[tuple[str, list[str]]] = []

    async def upload_source(self, file_path: Path, folder_id: str) -> str:
        self.uploaded_files.append((file_path, folder_id))
        return f"fake-file-id-{len(self.uploaded_files)}"

    async def sync_to_notebook(
        self, notebook_id: str, drive_file_ids: list[str]
    ) -> SyncResult:
        self.synced_notebooks.append((notebook_id, drive_file_ids))
        return SyncResult(synced_count=len(drive_file_ids), errors=[])

    async def list_sources(self, notebook_id: str) -> list:
        return []


class FakeSecurityShield:
    """Test SecurityShield (always allows)."""

    async def shield_input(self, content: str) -> ShieldResult:
        return ShieldResult(
            allowed=True, sanitized_content=content, findings=[], raw_response=None
        )

    async def shield_output(self, content: str) -> ShieldResult:
        return ShieldResult(
            allowed=True, sanitized_content=content, findings=[], raw_response=None
        )