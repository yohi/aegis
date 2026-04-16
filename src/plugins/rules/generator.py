"""Generate .mdc files from YAML templates."""

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()


class RuleGenerator:
    """Generate .mdc files from YAML templates."""

    def __init__(self, template_dir: Path) -> None:
        self.template_dir = template_dir

    def generate(
        self,
        target_dir: Path,
        overrides: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> list[Path]:
        """Load YAML templates, apply overrides, write .mdc files."""
        # Bind correlation_id to logger for traceability
        local_logger = logger.bind(correlation_id=correlation_id) if correlation_id else logger
        
        overrides = overrides or {}
        generated: list[Path] = []

        for yaml_file in sorted(self.template_dir.glob("*.yaml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    template = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                local_logger.error("Failed to parse YAML", file=str(yaml_file), error=str(exc))
                continue

            # 1. Validation of template structure and types
            if not isinstance(template, dict):
                local_logger.warning("Skipping invalid template: not a dict", file=str(yaml_file))
                continue

            rule_name = template.get("name")
            description = template.get("description")
            if not isinstance(rule_name, str) or not isinstance(description, str):
                local_logger.warning(
                    "Skipping template: missing or invalid 'name'/'description'", 
                    file=str(yaml_file)
                )
                continue

            globs = template.get("globs", [])
            sections = template.get("sections", [])
            if not isinstance(globs, list) or not isinstance(sections, list):
                local_logger.warning(
                    "Skipping template: 'globs' or 'sections' must be a list", 
                    file=str(yaml_file)
                )
                continue

            # 2. Path Traversal Prevention: Sanitize rule_name
            if not re.match(r"^[a-zA-Z0-9_\-]+$", rule_name):
                local_logger.warning(
                    "Skipping template: invalid 'name' (path traversal risk)", 
                    name=rule_name, 
                    file=str(yaml_file)
                )
                continue

            if rule_name in overrides:
                rule_overrides = overrides[rule_name]
                if (
                    isinstance(rule_overrides, dict)
                    and isinstance(rule_overrides.get("globs"), list)
                ):
                    globs = rule_overrides["globs"]

            mdc_content = self._render_mdc(description, globs, sections)

            # 3. Secure output path construction
            target_dir.mkdir(parents=True, exist_ok=True)
            output_path = (target_dir / f"{rule_name}.mdc").resolve()
            
            # Verify the resolved path is inside target_dir
            if target_dir.resolve() not in output_path.parents:
                local_logger.error(
                    "Path traversal attempt detected during rule generation", 
                    name=rule_name,
                    path=str(output_path)
                )
                continue

            output_path.write_text(mdc_content, encoding="utf-8")
            generated.append(output_path)

            local_logger.info("Generated rule file", path=str(output_path))

        return generated

    def _render_mdc(
        self,
        description: str,
        globs: list[str],
        sections: list[dict[str, Any]],
    ) -> str:
        """Render .mdc file content with YAML frontmatter."""
        # Use safe YAML dump for frontmatter values to handle special characters
        frontmatter = {
            "description": description,
            "globs": globs,
            "alwaysApply": False,
        }
        
        # Explicitly control YAML flow style for a clean look
        fm_str = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
        
        lines: list[str] = ["---", fm_str.strip(), "---", ""]

        for section in sections:
            if not isinstance(section, dict):
                continue
            title = section.get("title", "")
            rules = section.get("rules", [])
            
            # Coerce rules to a list of strings and sanitize
            if isinstance(rules, str):
                rules = [rules]
            elif not isinstance(rules, list):
                rules = []

            lines.append(f"## {title}")
            lines.append("")
            for rule in rules:
                # Basic sanitization: remove potential markdown injection/formatting in list items
                sanitized_rule = str(rule).replace("\n", " ").strip()
                lines.append(f"- {sanitized_rule}")
            lines.append("")

        return "\n".join(lines)
