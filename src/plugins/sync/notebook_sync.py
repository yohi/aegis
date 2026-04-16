"""Pipeline to sync repository code into NotebookLM."""

from __future__ import annotations

import asyncio
import fnmatch
from pathlib import Path

import structlog

from core.config import SyncConfig
from core.protocols import SecurityShield
from core.types import SyncError, SyncReport
from plugins.sync.drive_client import DriveClient

logger = structlog.get_logger()


class NotebookSyncer:
    """Pipeline to sync repository code into NotebookLM."""

    def __init__(
        self,
        drive_client: DriveClient,
        security_shield: SecurityShield,
        config: SyncConfig,
    ) -> None:
        self.drive_client = drive_client
        self.security_shield = security_shield
        self.config = config

    async def sync_repository(self, repo_path: Path) -> SyncReport:
        """Sync a repository's matching files to NotebookLM."""
        target_files = self._collect_files(repo_path)
        synced_count = 0
        skipped_count = 0
        errors: list[str] = []
        drive_file_ids: list[str] = []

        for file_path in target_files:
            try:
                file_id = await self._process_and_upload_file(file_path)
                if file_id:
                    drive_file_ids.append(file_id)
                    synced_count += 1
                else:
                    skipped_count += 1
            except Exception as exc:
                errors.append(f"Processing failed for {file_path}: {exc}")
                skipped_count += 1

        if drive_file_ids:
            try:
                await self.drive_client.sync_to_notebook(self.config.notebook_id, drive_file_ids)
            except Exception as exc:
                raise SyncError(f"NotebookLM sync failed: {exc}") from exc

        return SyncReport(
            total_files=len(target_files),
            synced_count=synced_count,
            skipped_count=skipped_count,
            errors=errors,
        )

    async def _process_and_upload_file(self, file_path: Path) -> str | None:
        """Process a single file (size check, sync read, shield) and upload.
        
        Return file_id if successful, None if skipped.
        """
        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb > self.config.max_file_size_kb:
            logger.info(
                "File exceeds size limit, skipping",
                file=str(file_path),
                size_kb=file_size_kb,
                limit_kb=self.config.max_file_size_kb,
            )
            return None

        try:
            # Offload blocking I/O to a thread
            content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning("Binary file skipped", file=str(file_path))
            return None

        shield_result = await self.security_shield.shield_input(content)
        if not shield_result.allowed:
            logger.warning(
                "File blocked by security shield",
                file=str(file_path),
                findings=[f.category for f in shield_result.findings],
            )
            return None

        return await self.drive_client.upload_source(
            file_path, self.config.drive_folder_id
        )

    def _collect_files(self, repo_path: Path) -> list[Path]:
        """Collect files matching include patterns, excluding exclude patterns."""
        matched: list[Path] = []
        for pattern in self.config.file_patterns:
            for file_path in repo_path.glob(pattern):
                if not file_path.is_file():
                    continue
                relative = str(file_path.relative_to(repo_path))
                excluded = any(
                    fnmatch.fnmatch(relative, exc) for exc in self.config.exclude_patterns
                )
                if not excluded:
                    matched.append(file_path)
        return sorted(set(matched))
