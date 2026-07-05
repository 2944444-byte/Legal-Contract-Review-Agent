"""Report assembly tests: sorting, summary, markdown, JSON."""

import json

from legal_agent import review_contract
from legal_agent.agent.tools import (
    analyze_clause,
    build_report,
    extract_clauses,
    load_document,
    render_markdown,
)
from legal_agent.domain.schemas import Severity


def test_findings_sorted_by_severity(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer", jurisdiction="US-DE")
    ranks = [f.severity.rank for f in report.findings]
    assert ranks == sorted(ranks, reverse=True), "findings must be most-severe first"


def test_report_has_clause_count_and_summary(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer")
    assert report.clause_count >= 11
    assert report.executive_summary
    assert "Buyer" in report.executive_summary


def test_markdown_renders_and_includes_citations(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer", jurisdiction="US-DE")
    md = render_markdown(report)
    assert md.startswith("# Contract Risk Report")
    assert "## Findings" in md
    assert "## Redline appendix" in md
    assert "Suggested redline" in md


def test_json_is_valid_and_roundtrips(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer")
    payload = report.model_dump_json()
    data = json.loads(payload)
    assert data["perspective"] == "Buyer"
    assert "findings" in data
    assert "disclaimer" in data


def test_empty_findings_report():
    """A document with no risky clauses still produces a valid report."""
    from legal_agent.domain.schemas import Document

    doc = Document(path="mem.txt", text="This is a benign statement of intent.", source_format="txt")
    report = build_report([], doc, perspective="Buyer", clause_count=1)
    assert report.findings == []
    assert "No taxonomy risks" in report.executive_summary
    md = render_markdown(report)
    assert "No taxonomy risks were flagged" in md
