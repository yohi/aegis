"""Tests for plugins/rules/generator.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from plugins.rules.generator import RuleGenerator


class TestRuleGenerator:
    """Test MDC rule generation from YAML templates."""

    @pytest.fixture
    def template_dir(self, tmp_path: Path) -> Path:
        t_dir = tmp_path / "templates"
        t_dir.mkdir()
        
        # Valid template
        (t_dir / "security.yaml").write_text(yaml.dump({
            "name": "security",
            "description": "Security # guardrails",
            "globs": ["*.py"],
            "sections": [{"title": "Rules", "rules": ["No secrets"]}]
        }))
        
        # Invalid template (None)
        (t_dir / "empty.yaml").write_text("")
        
        # Invalid template (not a dict)
        (t_dir / "list.yaml").write_text("- item")

        # Missing name
        (t_dir / "no_name.yaml").write_text("description: missing name")

        return t_dir

    def test_generate_success_and_robustness(
        self, template_dir: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "output" / "rules"  # Nested path to test mkdir
        gen = RuleGenerator(template_dir)
        
        generated = gen.generate(target_dir)
        
        # Should only generate 1 file (security.mdc), others are invalid
        assert len(generated) == 1
        output_file = generated[0]
        assert output_file.name == "security.mdc"
        
        content = output_file.read_text(encoding="utf-8")
        # Check if description is quoted
        assert 'description: "Security # guardrails"' in content
        # Check if directory was created
        assert target_dir.exists()

    def test_generate_with_overrides(
        self, template_dir: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "output"
        gen = RuleGenerator(template_dir)
        
        overrides = {"security": {"globs": ["src/*.py"]}}
        generated = gen.generate(target_dir, overrides=overrides)
        
        content = generated[0].read_text(encoding="utf-8")
        assert 'globs: ["src/*.py"]' in content
