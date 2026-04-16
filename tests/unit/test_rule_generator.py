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
        assert output_file.exists()
        assert output_file.parent == target_dir
        
        content = output_file.read_text(encoding="utf-8")
        # yaml.safe_dump might use single quotes or double quotes depending on content
        expected_sq = "description: 'Security # guardrails'"
        expected_dq = 'description: "Security # guardrails"'
        assert expected_sq in content or expected_dq in content
        # Check if directory was created
        assert target_dir.exists()

    def test_generate_with_overrides(
        self, template_dir: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "output"
        gen = RuleGenerator(template_dir)
        
        overrides = {"security": {"globs": ["src/*.py"]}}
        generated = gen.generate(target_dir, overrides=overrides)
        
        assert len(generated) == 1
        content = generated[0].read_text(encoding="utf-8")
        assert "globs:\n- src/*.py" in content

    def test_generate_with_invalid_overrides(
        self, template_dir: Path, tmp_path: Path
    ) -> None:
        target_dir = tmp_path / "output_invalid"
        gen = RuleGenerator(template_dir)
        
        # This should not raise AttributeError even if 'security' override is not a dict
        overrides = {"security": "invalid_type_not_a_dict"}
        generated = gen.generate(target_dir, overrides=overrides)
        
        assert len(generated) == 1
        assert generated[0].name == "security.mdc"
