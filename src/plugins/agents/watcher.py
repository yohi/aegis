"""Watch for task completion files and collect results."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
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
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            results = await self.collect_results(task_ids)
            all_done = all(
                results.get(tid) is not None
                and results[tid].status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                for tid in task_ids
            )
            if all_done:
                return [results[tid] for tid in task_ids]
            await asyncio.sleep(self.poll_interval)

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
        import re

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
            # Strip leading HTML comments
            while True:
                match = re.match(r"^\s*<!--.*?-->", response_section, flags=re.DOTALL)
                if not match:
                    break
                response_section = response_section[match.end():].strip()

            if response_section:
                response = response_section

        # Extract Objective
        objective = ""
        if "## Objective" in body:
            section = body.split("## Objective", 1)[1]
            objective = section.split("##", 1)[0].strip()

        # Extract Target Files
        target_files = []
        if "## Target Files" in body:
            section = body.split("## Target Files", 1)[1]
            section = section.split("##", 1)[0].strip()
            for line in section.splitlines():
                stripped = line.strip().lstrip("- ").strip("`")
                if stripped and stripped != "(none)":
                    target_files.append(Path(stripped))

        # Extract Constraints
        constraints = []
        if "## Constraints" in body:
            section = body.split("## Constraints", 1)[1]
            section = section.split("##", 1)[0].strip()
            for line in section.splitlines():
                stripped = line.strip().lstrip("- ").strip("`")
                if stripped and stripped != "(none)":
                    constraints.append(stripped)

        created_str = frontmatter.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_str)
        except (ValueError, TypeError):
            created_at = datetime.now(tz=timezone.utc)

        completed_at = None
        completed_str = frontmatter.get("completed_at")
        if completed_str:
            try:
                completed_at = datetime.fromisoformat(completed_str)
            except (ValueError, TypeError):
                pass

        try:
            return TaskMessage(
                task_id=frontmatter["task_id"],
                sender=AgentRole(frontmatter.get("sender", "techlead")),
                receiver=AgentRole(frontmatter.get("receiver", "techlead")),
                status=TaskStatus(frontmatter.get("status", "pending")),
                priority=Priority(frontmatter.get("priority", "medium")),
                created_at=created_at,
                completed_at=completed_at,
                objective=objective,
                target_files=target_files,
                constraints=constraints,
                depends_on=frontmatter.get("depends_on", []),
                response=response,
            )
        except ValueError as e:
            logger.warning(
                "Invalid enum value in task file",
                path=str(file_path),
                task_id=frontmatter.get("task_id"),
                error=str(e),
            )
            return None
