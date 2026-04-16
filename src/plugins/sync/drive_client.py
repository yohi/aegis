"""Google Drive operations abstraction."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from core.types import SourceInfo, SyncResult


@runtime_checkable
class DriveClient(Protocol):
    """Google Drive operations abstraction."""

    async def upload_source(self, file_path: Path, folder_id: str) -> str: ...

    async def sync_to_notebook(self, notebook_id: str, drive_file_ids: list[str]) -> SyncResult: ...

    async def list_sources(self, notebook_id: str) -> list[SourceInfo]: ...
