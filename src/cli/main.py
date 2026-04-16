"""CLI entry point using typer."""

from __future__ import annotations

from pathlib import Path

import typer
import structlog

app = typer.Typer(
    name="llm-review",
    help="LLM Autonomous Review System CLI",
)

logger = structlog.get_logger()


@app.command()
def review(
    repo_path: Path = typer.Argument(..., help="Path to the repository to review", exists=True),
    notebook_id: str = typer.Option(
        ..., envvar="LLM_REVIEW_SYNC_NOTEBOOK_ID", help="NotebookLM notebook ID"
    ),
    project_id: str = typer.Option(
        ..., envvar="LLM_REVIEW_SECURITY_GCP_PROJECT_ID", help="GCP Project ID"
    ),
) -> None:
    """Run a review on the specified repository."""
    import asyncio
    from core.config import SecurityConfig
    from core.orchestrator import Orchestrator
    from core.types import ReviewRequest
    from plugins.security.model_armor import ModelArmorClient
    from plugins.security.middleware import ModelArmorMiddleware

    async def _run() -> None:
        armor_client = ModelArmorClient(project_id=project_id)
        middleware = ModelArmorMiddleware(client=armor_client)
        orch = Orchestrator(shield=middleware)

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
            typer.echo(f"❌ Review failed: {exc}", err=True)
            raise typer.Exit(code=1)
        finally:
            await armor_client.close()

    asyncio.run(_run())


@app.command()
def generate_rules(
    template_dir: Path = typer.Argument(..., help="Path to YAML template directory", exists=True),
    output_dir: Path = typer.Argument(..., help="Output directory for .mdc files"),
) -> None:
    """Generate Cursor .mdc rule files from YAML templates."""
    from plugins.rules.generator import RuleGenerator

    output_dir.mkdir(parents=True, exist_ok=True)
    gen = RuleGenerator(template_dir)
    generated = gen.generate(output_dir)
    for path in generated:
        typer.echo(f"  ✅ Generated: {path}")
    typer.echo(f"\n{len(generated)} rule file(s) generated.")


if __name__ == "__main__":
    app()
