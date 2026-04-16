"""Tests for CLI entry point."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app


class TestCLIReview:
    """Test CLI review command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_review_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "Run a review on the specified repository" in result.stdout

    def test_review_repo_not_found(self, runner: CliRunner) -> None:
        result = runner.invoke(
            app,
            [
                "review",
                "/nonexistent/path",
                "--notebook-id",
                "test-id",
                "--project-id",
                "test-project",
            ],
        )
        assert result.exit_code == 2


class TestCLIGenerateRules:
    """Test CLI generate-rules command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_generate_rules_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["generate-rules", "--help"])
        assert result.exit_code == 0
        assert "Generate Cursor .mdc rule files" in result.stdout

    def test_generate_rules_with_template(self, runner: CliRunner, tmp_path: Path) -> None:
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.yaml").write_text("""
name: "001-test"
description: "Test rule"
globs:
  - "**/*.py"
sections:
  - title: "Test"
    rules:
      - "Test rule 1"
""")
        output_dir = tmp_path / "output"

        result = runner.invoke(
            app,
            [
                "generate-rules",
                str(template_dir),
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert "rule file(s) generated" in result.stdout

    def test_generate_rules_invalid_json(self, runner: CliRunner, tmp_path: Path) -> None:
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.yaml").write_text("name: '001-test'")
        output_dir = tmp_path / "output"

        result = runner.invoke(
            app,
            [
                "generate-rules",
                str(template_dir),
                str(output_dir),
                "--glob-overrides",
                "invalid json",
            ],
        )
        assert result.exit_code == 2
