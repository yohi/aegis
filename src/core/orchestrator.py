"""Review pipeline orchestrator."""

from __future__ import annotations

import asyncio
from asyncio import Semaphore
from datetime import UTC
from pathlib import Path

import structlog

from .protocols import SecurityShield
from .types import (
    ReviewRequest,
    ReviewResult,
    ReviewSystemError,
    SecurityBlockedError,
    SyncError,
)

logger = structlog.get_logger()


class Orchestrator:
    """Coordinates the full review pipeline."""


    def __init__(
        self,
        shield: SecurityShield,
        repo_path: Path,
        max_concurrent_shields: int = 10,
    ) -> None:
        if not isinstance(max_concurrent_shields, int) or max_concurrent_shields < 1:
            raise ValueError("max_concurrent_shields must be an int >= 1")
        self._io_semaphore = Semaphore(10)
        self._shield_semaphore = Semaphore(max_concurrent_shields)
        self.shield = shield
        self.repo_path = repo_path

    async def _read_file(self, file: Path) -> tuple[Path, str]:
        """Read a file asynchronously without blocking the event loop."""
        async with self._io_semaphore:
            try:
                content = await asyncio.to_thread(file.read_text, encoding="utf-8")
            except (UnicodeDecodeError, OSError) as exc:
                raise SyncError(
                    f"Cannot read {file}: {exc}"
                ) from exc
        return file, content

    async def _shield_file(self, file: Path, content: str, request_id: str) -> None:
        """Shield a single file input and raise error if blocked."""
        async with self._shield_semaphore:
            result = await self.shield.shield_input(content)

        if not result.allowed:
            categories = [f.category for f in result.findings]
            logger.error(
                "security_input_blocked",
                message=f"Input blocked for {file.name}",
                file=file.name,
                categories=categories,
                request_id=request_id,
            )
            raise SecurityBlockedError(
                f"Input blocked for {file.name}: {categories}"
            )

    async def run_review(self, request: ReviewRequest) -> ReviewResult:
        """Execute the full review pipeline."""
        sanitized_files = []
        repo_root = request.repo_path.resolve()
        for f in request.target_files:
            # Resolve path against request.repo_path and verify it's a descendant
            resolved_path = (repo_root / f).resolve()
            if repo_root not in resolved_path.parents and resolved_path != repo_root:
                logger.error("security_path_traversal_attempt_detected", path=str(f))
                raise SecurityBlockedError(f"Path traversal attempt detected: {f}")
            sanitized_files.append(resolved_path)

        file_contents = await asyncio.gather(*(self._read_file(f) for f in sanitized_files))

        # Parallelize security shielding for all files using TaskGroup for robust cancellation
        try:
            async with asyncio.TaskGroup() as tg:
                for file, content in file_contents:
                    tg.create_task(self._shield_file(file, content, request.request_id))
        except ExceptionGroup as eg:
            # Re-raise the first SecurityBlockedError or other ReviewSystemError
            # to maintain API consistency. If multiple files are blocked,
            # TaskGroup collects all, but we only need to report the first failure.
            if len(eg.exceptions) == 1:
                raise eg.exceptions[0] from eg

            # Prioritize SecurityBlockedError, then any ReviewSystemError
            for exc in eg.exceptions:
                if isinstance(exc, SecurityBlockedError):
                    raise exc from eg
            for exc in eg.exceptions:
                if isinstance(exc, ReviewSystemError):
                    raise exc from eg
            raise  # Fallback for unexpected exceptions

        from datetime import datetime

        logger.info(
            "state_transition",
            timestamp=datetime.now(UTC).isoformat(),
            request_id=request.request_id,
            actor="system",
            previous_state="pending",
            next_state="in_progress",
        )
        review_output = ReviewResult(
            request_id=request.request_id,
            status="in_progress",
            findings=(),
            summary="Review in progress.",
        )

        output_result = await self.shield.shield_output(review_output.summary)
        if not output_result.allowed:
            review_output = review_output.with_redacted_summary()
        else:
            review_output = review_output.with_summary(output_result.sanitized_content)

        return review_output
