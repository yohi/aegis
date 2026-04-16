"""Generate and distribute task files with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path

import structlog

from .protocol import TaskMessage

logger = structlog.get_logger()


class TaskDispatcher:
    """Generate and distribute task files."""

    def __init__(self, workspace_dir: Path) -> None:
        self.task_dir = workspace_dir / ".review" / "tasks"
        self.task_dir.mkdir(parents=True, exist_ok=True)

    async def dispatch(self, message: TaskMessage) -> Path:
        """Convert TaskMessage to Markdown and write atomically.

        Uses write-then-rename for crash safety.
        """
        content = self._render_markdown(message)
        filename = self._generate_filename(message)
        target = self.task_dir / filename

        await self._atomic_write(target, content)
        logger.info("Task dispatched", path=str(target), task_id=message.task_id)
        return target

    def _generate_filename(self, message: TaskMessage) -> str:
        date = message.created_at.strftime("%Y%m%d")
        unique_id = uuid.uuid4().hex[:8]
        return f"TASK-{date}-{unique_id}-{message.sender}-to-{message.receiver}.md"

    def _render_markdown(self, message: TaskMessage) -> str:
        """Render TaskMessage as Markdown with YAML frontmatter."""
        target_files_str = "\n".join(
            f"- `{f}`" for f in message.target_files
        )
        constraints_str = "\n".join(
            f"- {c}" for c in message.constraints
        )
        depends_str = json.dumps(message.depends_on)
        completed_at_str = json.dumps(message.completed_at.isoformat()) if message.completed_at else "null"

        return f"""---
task_id: {json.dumps(message.task_id)}
sender: {json.dumps(message.sender)}
receiver: {json.dumps(message.receiver)}
status: {json.dumps(message.status)}
priority: {json.dumps(message.priority)}
created_at: {json.dumps(message.created_at.isoformat())}
completed_at: {completed_at_str}
depends_on: {depends_str}
---

## Objective
{message.objective}

## Target Files
{target_files_str or "(none)"}

## Constraints
{constraints_str or "(none)"}

## Expected Output Format
Return findings as structured YAML in the response section below.

---
## Response
<!-- receiver writes results here -->
"""

    async def _atomic_write(self, target: Path, content: str) -> None:
        """Write content atomically using write-then-rename."""
        import asyncio
        await asyncio.to_thread(self._sync_atomic_write, target, content)

    def _sync_atomic_write(self, target: Path, content: str) -> None:
        dir_path = target.parent
        fd, tmp_path = tempfile.mkstemp(
            suffix=".tmp", prefix=target.stem, dir=dir_path
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.rename(tmp_path, target)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
