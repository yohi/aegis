"""Generate .mdc files from YAML templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

import structlog

logger = structlog.get_logger()


class RuleGenerator:
    """Generate .mdc files from YAML templates."""

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir

    def generate(
        self,
        target_dir: Path,
        overrides: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Load YAML templates, apply overrides, write .mdc files."""
        overrides = overrides or {}
        generated: list[Path] = []

        for yaml_file in sorted(self.template_dir.glob("*.yaml")):
            with open(yaml_file) as f:
                template = yaml.safe_load(f)

            rule_name = template["name"]
            description = template["description"]
            globs = template.get("globs", [])
            sections = template.get("sections", [])

            if rule_name in overrides:
                rule_overrides = overrides[rule_name]
                if "globs" in rule_overrides:
                    globs = rule_overrides["globs"]

            mdc_content = self._render_mdc(description, globs, sections)

            output_path = target_dir / f"{rule_name}.mdc"
            output_path.write_text(mdc_content)
            generated.append(output_path)

            logger.info("Generated rule file", path=str(output_path))

        return generated

    def _render_mdc(
        self,
        description: str,
        globs: list[str],
        sections: list[dict[str, Any]],
    ) -> str:
        """Render .mdc file content with YAML frontmatter."""
        lines: list[str] = []

        lines.append("---")
        lines.append(f"description: {description}")
        glob_str = ", ".join(f'"{g}"' for g in globs)
        lines.append(f"globs: [{glob_str}]")
        lines.append("alwaysApply: false")
        lines.append("---")
        lines.append("")

        for section in sections:
            title = section.get("title", "")
            rules = section.get("rules", [])
            lines.append(f"## {title}")
            lines.append("")
            for rule in rules:
                lines.append(f"- {rule}")
            lines.append("")

        return "\n".join(lines)
