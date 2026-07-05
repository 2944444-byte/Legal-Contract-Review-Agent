"""Legal Contract Review Agent — Phase 1 (contract flagger MVP).

Decision-support software for reviewing your OWN contract. NOT legal advice.
See SPEC.md §0 for the guardrails this tool is built around.

The public surface is the four Phase-1 tools plus :func:`review_contract`, which
wires them end-to-end: load_document -> extract_clauses -> analyze_clause ->
build_report.
"""

from __future__ import annotations

from .agent.tools import (
    analyze_clause,
    build_report,
    extract_clauses,
    get_analyzer,
    load_document,
    render_markdown,
)
from .domain.jurisdictions import normalize as normalize_jurisdiction
from .domain.schemas import Report

__version__ = "0.1.0"

__all__ = [
    "review_contract",
    "load_document",
    "extract_clauses",
    "analyze_clause",
    "build_report",
    "render_markdown",
    "Report",
]


def review_contract(
    path: str,
    perspective: str,
    jurisdiction: str | None = None,
    backend: str = "heuristic",
    api_key: str | None = None,
    local_model: str = "llama3.1",
    base_url: str | None = None,
    prefer_model: bool | None = None,
) -> Report:
    """Run the full Phase-1 pipeline and return a :class:`Report`.

    Parameters
    ----------
    path:
        Path to a PDF/DOCX/TXT contract.
    perspective:
        Whose side we're on (e.g. ``"buyer"``, ``"vendor"``, ``"employee"``).
    jurisdiction:
        Jurisdiction code (e.g. ``"US-CA"``). ``None`` means unknown, and
        jurisdiction-specific conclusions are withheld.
    backend:
        ``"heuristic"`` (default, offline, free), ``"local"`` (local Ollama
        model, free, keyless), or ``"claude"`` (Anthropic API, needs a key).
    local_model / base_url:
        Model name and server URL for the ``"local"`` backend.
    prefer_model:
        Backward-compatible alias for ``backend="claude"``.
    """
    document = load_document(path)
    clauses = extract_clauses(document)
    juris = normalize_jurisdiction(jurisdiction)
    analyzer = get_analyzer(
        backend=backend,
        api_key=api_key,
        local_model=local_model,
        base_url=base_url,
        prefer_model=prefer_model,
    )

    findings = []
    for clause in clauses:
        findings.extend(analyze_clause(clause, perspective, juris, analyzer=analyzer))

    return build_report(
        findings,
        document,
        perspective=perspective,
        jurisdiction=juris,
        clause_count=len(clauses),
    )
