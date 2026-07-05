"""Command-line interface (SPEC §12, §13).

Phase 1 exposes:

    legal-agent review <file> --side buyer --jurisdiction US-CA

which runs the pipeline and prints a Markdown risk report (or JSON with
``--format json``). A ``chat`` subcommand is stubbed for Phase 2.
"""

from __future__ import annotations

import sys

import typer

from . import review_contract
from .agent.tools import render_markdown
from .domain.jurisdictions import is_known, normalize

app = typer.Typer(
    add_completion=False,
    help="Legal Contract Review Agent — flags risky clauses in your contract. "
    "Decision-support software, NOT legal advice.",
)


@app.command()
def review(
    file: str = typer.Argument(..., help="Path to a PDF/DOCX/TXT contract."),
    side: str = typer.Option(
        ..., "--side", "-s", help="Whose perspective (e.g. buyer, vendor, employee)."
    ),
    jurisdiction: str = typer.Option(
        None,
        "--jurisdiction",
        "-j",
        help="Jurisdiction code, e.g. US-CA. Omit if unknown.",
    ),
    output_format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format: markdown | json."
    ),
    out: str = typer.Option(
        None, "--out", "-o", help="Write output to this file instead of stdout."
    ),
    use_model: bool = typer.Option(
        False,
        "--use-model/--no-model",
        help="Use the Claude-backed analyzer (needs ANTHROPIC_API_KEY). "
        "Default is the offline heuristic analyzer.",
    ),
) -> None:
    """Review a contract and produce a risk report with citations and redlines."""
    norm = normalize(jurisdiction)
    if jurisdiction and not is_known(norm):
        typer.secho(
            f"Note: jurisdiction '{jurisdiction}' is not in the registry; "
            "jurisdiction-specific conclusions will be withheld.",
            fg=typer.colors.YELLOW,
            err=True,
        )

    try:
        report = review_contract(
            file,
            perspective=side,
            jurisdiction=jurisdiction,
            prefer_model=use_model,
        )
    except FileNotFoundError:
        typer.secho(f"File not found: {file}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)
    except Exception as exc:  # surface parse/other errors cleanly
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    if output_format == "json":
        payload = report.model_dump_json(indent=2)
    else:
        payload = render_markdown(report)

    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        typer.secho(f"Wrote {output_format} report to {out}", fg=typer.colors.GREEN, err=True)
    else:
        sys.stdout.write(payload + "\n")


@app.command()
def chat() -> None:
    """Conversational REPL (Phase 2 — not yet implemented)."""
    typer.secho(
        "The conversational agent (Phase 2) is not implemented yet. "
        "Use `legal-agent review <file> --side <party>` for now.",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=0)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
