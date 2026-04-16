"""CLI entry point using typer."""

from __future__ import annotations

from pathlib import Path

import structlog
import typer  # noqa: B008

logger = structlog.get_logger()

app = typer.Typer(
    name="llm-review",
    help="LLM Autonomous Review System CLI",
)


@app.command()
def review(
    repo_path: Path = typer.Argument(  # noqa: B008
        ..., help="Path to the repository to review", exists=True
    ),
    notebook_id: str = typer.Option(  # noqa: B008
        ..., envvar="LLM_REVIEW_SYNC_NOTEBOOK_ID", help="NotebookLM notebook ID"
    ),
    project_id: str = typer.Option(  # noqa: B008
        ..., envvar="LLM_SECURITY_GCP_PROJECT_ID", help="GCP Project ID"
    ),
    max_concurrent_shields: int = typer.Option(10, help="Maximum concurrent shield operations"),
) -> None:
    """Run a review on the specified repository."""
    import asyncio

    from core.orchestrator import Orchestrator
    from core.types import ReviewRequest
    from plugins.security.middleware import ModelArmorMiddleware
    from plugins.security.model_armor import ModelArmorClient

    async def _run() -> None:
        armor_client = ModelArmorClient(project_id=project_id)
        middleware = ModelArmorMiddleware(client=armor_client)
        orch = Orchestrator(
            shield=middleware,
            repo_path=repo_path,
            max_concurrent_shields=max_concurrent_shields,
        )

        target_files = list(repo_path.glob("**/*.py"))
        request = ReviewRequest(
            request_id=f"cli-{repo_path.name}",
            repo_path=repo_path,
            target_files=target_files[:50],
        )

        try:
            result = await orch.run_review(request)
            typer.echo(f"✅ Review completed: {result.status}")
            typer.echo(f"   Findings: {len(result.findings)}")
            typer.echo(f"   Summary: {result.summary}")
        except Exception as exc:
            typer.echo(f"❌ Review failed: {exc}", err=True)  # noqa: B904
            raise typer.Exit(code=1) from exc
        finally:
            await armor_client.close()

    asyncio.run(_run())


@app.command()
def generate_rules(
    template_dir: Path = typer.Argument(  # noqa: B008
        ..., help="Path to YAML template directory", exists=True
    ),
    output_dir: Path = typer.Argument(  # noqa: B008
        ..., help="Output directory for .mdc files"
    ),
    glob_overrides: str = typer.Option(  # noqa: B008
        "",
        help='JSON overrides (e.g., \'{"001-security": {"globs": ["**/*.rs"]}}\')',
    ),
) -> None:
    """Generate Cursor .mdc rule files from YAML templates."""
    import json

    from plugins.rules.generator import RuleGenerator

    output_dir.mkdir(parents=True, exist_ok=True)
    overrides: dict[str, object] | None = None
    if glob_overrides.strip():
        try:
            overrides = json.loads(glob_overrides)
        except json.JSONDecodeError as e:  # noqa: B904
            raise typer.BadParameter(f"Invalid JSON for glob_overrides: {e}") from e

    gen = RuleGenerator(template_dir)
    generated = gen.generate(output_dir, overrides=overrides)
    for path in generated:
        typer.echo(f"  ✅ Generated: {path}")
    typer.echo(f"\n{len(generated)} rule file(s) generated.")


if __name__ == "__main__":
    app()
