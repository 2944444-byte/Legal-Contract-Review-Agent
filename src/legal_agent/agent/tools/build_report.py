"""Tool: build_report(findings, document, ...) -> Report + Markdown (SPEC §6).

Report assembly is deterministic. Findings are sorted by severity (most severe
first), an executive summary is computed, and the mandatory disclaimer is always
attached — it is injected here (and in the Markdown renderer) so it cannot be
skipped. Both a machine-readable :class:`Report` and a human-readable Markdown
string are produced.
"""

from __future__ import annotations

from ...domain.jurisdictions import describe as describe_jurisdiction
from ...domain.schemas import (
    DISCLAIMER,
    Document,
    Finding,
    Report,
    Severity,
)


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    # Most severe first; stable within a severity by clause id.
    return sorted(
        findings,
        key=lambda f: (-f.severity.rank, f.clause_id),
    )


def _executive_summary(
    findings: list[Finding], clause_count: int, perspective: str
) -> str:
    if not findings:
        return (
            f"No taxonomy risks were flagged across {clause_count} clause(s) from "
            f"the {perspective}'s perspective. This does not mean the contract is "
            "risk-free — review it with a qualified lawyer."
        )
    counts = {s: 0 for s in Severity}
    for f in findings:
        counts[f.severity] += 1
    parts = [
        f"{counts[s]} {s.value}"
        for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO)
        if counts[s]
    ]
    breakdown = ", ".join(parts)
    top = _sort_findings(findings)[:3]
    highlights = "; ".join(f"{f.clause_id}: {f.risk_type}" for f in top)
    return (
        f"Flagged {len(findings)} issue(s) across {clause_count} clause(s) from "
        f"the {perspective}'s perspective ({breakdown}). "
        f"Most significant: {highlights}."
    )


def build_report(
    findings: list[Finding],
    document: Document,
    perspective: str,
    jurisdiction: str | None = None,
    clause_count: int | None = None,
) -> Report:
    """Assemble findings into a structured, sorted :class:`Report`."""
    sorted_findings = _sort_findings(findings)
    count = clause_count if clause_count is not None else 0
    return Report(
        document_path=document.path,
        document_title=document.title,
        perspective=perspective,
        jurisdiction=jurisdiction,
        findings=sorted_findings,
        clause_count=count,
        executive_summary=_executive_summary(sorted_findings, count, perspective),
        disclaimer=DISCLAIMER,
    )


_SEVERITY_LABEL = {
    Severity.CRITICAL: "🔴 CRITICAL",
    Severity.HIGH: "🟠 HIGH",
    Severity.MEDIUM: "🟡 MEDIUM",
    Severity.LOW: "🔵 LOW",
    Severity.INFO: "⚪ INFO",
}


def render_markdown(report: Report) -> str:
    """Render a :class:`Report` as a human-readable Markdown risk report."""
    lines: list[str] = []
    title = report.document_title or report.document_path
    lines.append(f"# Contract Risk Report — {title}")
    lines.append("")
    lines.append(f"> **⚠️ DRAFT ANALYSIS — NOT LEGAL ADVICE.** {report.disclaimer}")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **File:** `{report.document_path}`")
    lines.append(f"- **Perspective:** {report.perspective}")
    lines.append(f"- **Jurisdiction:** {describe_jurisdiction(report.jurisdiction)}")
    lines.append(f"- **Clauses analyzed:** {report.clause_count}")
    counts = report.severity_counts()
    counts_str = ", ".join(
        f"{counts[s.value]} {s.value}"
        for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO)
    )
    lines.append(f"- **Findings by severity:** {counts_str}")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    if not report.findings:
        lines.append("_No taxonomy risks were flagged._")
        lines.append("")
    else:
        for i, f in enumerate(report.findings, 1):
            label = _SEVERITY_LABEL[f.severity]
            lines.append(f"### {i}. {label} — {f.risk_type}  ·  Clause {f.clause_id}")
            lines.append("")
            lines.append(f"- **Confidence:** {f.confidence.value}")
            lines.append(f"- **Why it matters:** {f.rationale}")
            lines.append("- **Cited text:**")
            lines.append("")
            for cl in f.citation.splitlines() or [f.citation]:
                lines.append(f"  > {cl}")
            lines.append("")
            lines.append(f"- **Suggested redline:** {f.suggested_redline}")
            lines.append("")

    lines.append("## Redline appendix")
    lines.append("")
    if report.findings:
        for f in report.findings:
            lines.append(f"- **Clause {f.clause_id} ({f.risk_type}):** {f.suggested_redline}")
    else:
        lines.append("_No redlines proposed._")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"_{report.disclaimer}_")
    lines.append("")
    return "\n".join(lines)
