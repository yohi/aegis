"""Watch for task completion files and collect results."""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
import structlog

from core.types import AgentTimeoutError
from .protocol import TaskMessage, TaskStatus, AgentRole, Priority

logger = structlog.get_logger()


class TaskWatcher:
    """Watch for task completion files and collect results."""

    def __init__(self, task_dir: Path, poll_interval: float = 2.0) -> None:
        self.task_dir = task_dir
        self.poll_interval = poll_interval

    async def wait_for_completion(
        self,
        task_ids: list[str],
        timeout: float = 300.0,
    ) -> list[TaskMessage]:
        """Poll until all specified tasks reach completed/failed status."""
        elapsed = 0.0
        while elapsed < timeout:
            results = await self.collect_results(task_ids)
            all_done = all(
                results.get(tid) is not None
                and results[tid].status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                for tid in task_ids
            )
            if all_done:
                return [results[tid] for tid in task_ids]
            await asyncio.sleep(self.poll_interval)
            elapsed += self.poll_interval

        raise AgentTimeoutError(
            f"Tasks {task_ids} did not complete within {timeout}s"
        )

    async def collect_results(self, task_ids: list[str]) -> dict[str, TaskMessage]:
        """Return completed task results as a dictionary."""
        results: dict[str, TaskMessage] = {}
        for md_file in self.task_dir.glob("*.md"):
            parsed = self._parse_task_file(md_file)
            if parsed and parsed.task_id in task_ids:
                results[parsed.task_id] = parsed
        return results

    def _parse_task_file(self, file_path: Path) -> TaskMessage | None:
        """Parse a task Markdown file into a TaskMessage."""
        content = file_path.read_text()
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            logger.warning("Failed to parse task file", path=str(file_path))
            return None

        if not frontmatter or "task_id" not in frontmatter:
            return None

        # Extract response section
        body = parts[2]
        response = None
        if "## Response" in body:
            response_section = body.split("## Response", 1)[1].strip()
            if response_section and not response_section.startswith("<!--"):
                response = response_section

        from datetime import datetime

        created_str = frontmatter.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_str)
        except (ValueError, TypeError):
            created_at = datetime.now()

        return TaskMessage(
            task_id=frontmatter["task_id"],
            sender=AgentRole(frontmatter.get("sender", "techlead")),
            receiver=AgentRole(frontmatter.get("receiver", "techlead")),
            status=TaskStatus(frontmatter.get("status", "pending")),
            priority=Priority(frontmatter.get("priority", "medium")),
            created_at=created_at,
            objective="",
            target_files=[],
            constraints=[],
            depends_on=frontmatter.get("depends_on", []),
            response=response,
        )
