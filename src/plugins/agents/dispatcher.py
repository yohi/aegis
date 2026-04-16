"""Generate and distribute task files with atomic writes."""

from __future__ import annotations

import os
import tempfile
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
        """Convert TaskMessage to Markdown and write atomically."""
        content = self._render_markdown(message)
        filename = self._generate_filename(message)
        target = self.task_dir / filename

        await self._atomic_write(target, content)
        logger.info("Task dispatched", path=str(target), task_id=message.task_id)
        return target

    def _generate_filename(self, message: TaskMessage) -> str:
        date = message.created_at.strftime("%Y%m%d")
        seq = self._next_sequence_id()
        return f"TASK-{date}-{seq:03d}-{message.sender}-to-{message.receiver}.md"

    def _next_sequence_id(self) -> int:
        existing = [f for f in self.task_dir.glob("*.md") if not f.name.endswith(".tmp")]
        if not existing:
            return 1
        max_id = 0
        for f in existing:
            parts = f.stem.split("-")
            if len(parts) >= 3:
                try:
                    max_id = max(max_id, int(parts[2]))
                except ValueError:
                    continue
        return max_id + 1

    def _render_markdown(self, message: TaskMessage) -> str:
        target_files_str = "\n".join(f"- `{f}`" for f in message.target_files)
        constraints_str = "\n".join(f"- {c}" for c in message.constraints)
        depends_str = str(message.depends_on) if message.depends_on else "[]"

        return f"""---
task_id: "{message.task_id}"
sender: "{message.sender}"
receiver: "{message.receiver}"
status: "{message.status}"
priority: "{message.priority}"
created_at: "{message.created_at.isoformat()}"
completed_at: null
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
        dir_path = target.parent
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", prefix=target.stem, dir=dir_path)
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.rename(tmp_path, target)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise
