"""CLI entry point for the Autonomous Political Accountability System."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure the project root is importable when run as `python main.py`.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = typer.Typer(
    name="political-accountability",
    help="Autonomous Political Accountability and Normative Discourse System",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    query: str = typer.Option(
        "India parliament corruption", help="News query to monitor"
    )
) -> None:
    """Start the full pipeline for a given news query."""
    from src.orchestration.langgraph_workflow import AccountabilityWorkflow

    console.print(
        Panel(
            f"[bold green]Starting pipeline for:[/bold green] [cyan]{query}[/cyan]",
            title="Accountability System",
        )
    )
    workflow = AccountabilityWorkflow()
    state = workflow.run(query)
    console.print_json(data=_serialisable(state))


@app.command()
def dashboard() -> None:
    """Launch the Streamlit monitoring dashboard."""
    dashboard_path = Path(__file__).parent / "src" / "dashboard" / "app.py"
    console.print("[bold]Launching dashboard...[/bold]")
    subprocess.run(  # noqa: S603 S607
        ["streamlit", "run", str(dashboard_path)],
        check=False,
    )


@app.command()
def review() -> None:
    """Show pending HITL reviews."""
    from src.publishing.hitl_queue import HITLQueue

    queue = HITLQueue()
    pending = queue.get_pending_reviews()
    if not pending:
        console.print("[green]No pending reviews.[/green]")
        return

    table = Table(title="Pending HITL Reviews")
    table.add_column("Review ID", style="cyan")
    table.add_column("Created At", style="magenta")
    table.add_column("Post Preview", max_width=60)

    for item in pending:
        table.add_row(
            item["review_id"][:12] + "…",
            item["created_at"][:19],
            item["post_content"][:57] + "…" if len(item["post_content"]) > 60 else item["post_content"],
        )
    console.print(table)


@app.command()
def analyze(
    query: str = typer.Argument(..., help="Topic to analyse")
) -> None:
    """Run a one-off analysis of a political topic."""
    from src.orchestration.crew_orchestrator import AccountabilityCrew
    from src.ingestion.news_ingestion import NewsIngestionAgent

    console.print(f"[bold]Analysing:[/bold] {query}")
    news_agent = NewsIngestionAgent()
    events = news_agent.fetch_events(query, max_results=3)
    if not events:
        console.print("[red]No events found.[/red]")
        raise typer.Exit(code=1)

    crew = AccountabilityCrew()
    event = events[0].__dict__
    draft = crew.run_analysis(event)
    console.print(Panel(draft, title=f"Analysis: {event.get('title', query)[:60]}"))


def _serialisable(state: dict) -> dict:
    """Strip non-serialisable values for console output."""
    safe: dict = {}
    for k, v in state.items():
        try:
            import json
            json.dumps(v)
            safe[k] = v
        except (TypeError, ValueError):
            safe[k] = str(v)
    return safe


if __name__ == "__main__":
    app()
