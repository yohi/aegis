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

    def test_review_success(self, runner: CliRunner, tmp_path: Path) -> None:
        from unittest.mock import AsyncMock, patch

        # Create a dummy repo
        repo_path = tmp_path / "dummy-repo"
        repo_path.mkdir()
        (repo_path / "main.py").write_text("print('hello')")

        # Mock dependencies
        with patch("plugins.security.model_armor.ModelArmorClient") as mock_armor_cls, \
             patch("core.orchestrator.Orchestrator") as mock_orch_cls:
            
            mock_armor = mock_armor_cls.return_value
            mock_armor.close = AsyncMock()
            
            mock_orch = mock_orch_cls.return_value

            from core.types import ReviewResult
            mock_result = ReviewResult(
                request_id="cli-dummy-repo",
                status="completed",
                findings=(),
                summary="Clean review",
            )
            mock_orch.run_review = AsyncMock(return_value=mock_result)

            result = runner.invoke(
                app,
                [
                    "review",
                    str(repo_path),
                    "--notebook-id",
                    "test-id",
                    "--project-id",
                    "test-project",
                ],
            )

            assert result.exit_code == 0
            assert "✅ Review completed: completed" in result.stdout
            assert "Findings: 0" in result.stdout
            assert "Summary: Clean review" in result.stdout

            mock_armor_cls.assert_called_once_with(project_id="test-project")
            mock_orch_cls.assert_called_once()
            mock_orch.run_review.assert_called_once()

    def test_review_truncation_warning(self, runner: CliRunner, tmp_path: Path) -> None:
        from unittest.mock import AsyncMock, patch

        # Create a dummy repo with 3 files
        repo_path = tmp_path / "trunc-repo"
        repo_path.mkdir()
        (repo_path / "a.py").write_text("a")
        (repo_path / "b.py").write_text("b")
        (repo_path / "c.py").write_text("c")

        # Mock dependencies
        with patch("plugins.security.model_armor.ModelArmorClient") as mock_armor_cls, \
             patch("core.orchestrator.Orchestrator") as mock_orch_cls, \
             patch("cli.main.logger") as mock_logger:
            
            mock_armor = mock_armor_cls.return_value
            mock_armor.close = AsyncMock()
            mock_orch = mock_orch_cls.return_value

            from core.types import ReviewResult
            mock_result = ReviewResult(
                request_id="cli-trunc-repo",
                status="completed",
                findings=(),
                summary="Clean review",
            )
            mock_orch.run_review = AsyncMock(return_value=mock_result)

            # Limit to 2 files
            result = runner.invoke(
                app,
                [
                    "review",
                    str(repo_path),
                    "--notebook-id",
                    "test-id",
                    "--project-id",
                    "test-project",
                    "--max-files",
                    "2",
                ],
            )

            assert result.exit_code == 0
            
            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            args, kwargs = mock_logger.warning.call_args
            assert args[0] == "file_truncation_warning"
            assert kwargs["max_files"] == 2

            # Verify only 2 files were passed to ReviewRequest
            # Since Orchestrator.run_review is called with the request, check its call
            call_args = mock_orch.run_review.call_args[0][0]
            assert len(call_args.target_files) == 2


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

        # Verify generated file content
        generated_file = output_dir / "001-test.mdc"
        assert generated_file.exists()
        content = generated_file.read_text()
        assert "description: Test rule" in content
        assert "## Test" in content
        assert "- Test rule 1" in content

    def test_generate_rules_invalid_json(self, runner: CliRunner, tmp_path: Path) -> None:
        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        (template_dir / "test.yaml").write_text("name: '001-test'")
        output_dir = tmp_path / "output"

        # Syntactically invalid JSON
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
        assert "Invalid JSON" in result.output

        # Valid JSON but not a dict
        result = runner.invoke(
            app,
            [
                "generate-rules",
                str(template_dir),
                str(output_dir),
                "--glob-overrides",
                "[]",
            ],
        )
        assert result.exit_code == 2
        assert "must be a JSON object (dict)" in result.output
