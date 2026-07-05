"""Regression tests: planted problems are flagged at the right severity.

These target the deterministic (offline) analyzer so they are reproducible
without an API key (SPEC §14).
"""

from legal_agent.agent.tools import analyze_clause, extract_clauses, load_document
from legal_agent.domain.schemas import CharSpan, Clause, Severity


def _review(path, side="Buyer"):
    doc = load_document(path)
    clauses = extract_clauses(doc)
    findings = []
    for c in clauses:
        findings.extend(analyze_clause(c, side, "US-DE"))
    return doc, clauses, findings


def test_flags_planted_problems(sample_nda_path):
    _, _, findings = _review(sample_nda_path)
    by_type = {f.risk_type for f in findings}
    for expected in [
        "auto_renewal",
        "uncapped_liability",
        "one_sided_indemnification",
        "ip_assignment_overreach",
        "non_compete",
        "unilateral_amendment",
        "forced_arbitration",
        "warranty_disclaimer",
        "confidentiality_asymmetry",
    ]:
        assert expected in by_type, f"expected to flag {expected}; got {sorted(by_type)}"


def test_severity_assignment(sample_nda_path):
    _, _, findings = _review(sample_nda_path)
    sev = {f.risk_type: f.severity for f in findings}
    assert sev["uncapped_liability"] == Severity.HIGH
    assert sev["one_sided_indemnification"] == Severity.HIGH
    assert sev["non_compete"] == Severity.HIGH
    assert sev["auto_renewal"] == Severity.MEDIUM
    assert sev["forced_arbitration"] == Severity.MEDIUM


def test_findings_map_to_correct_clauses(sample_nda_path):
    _, _, findings = _review(sample_nda_path)
    by_type = {f.risk_type: f for f in findings}
    assert by_type["uncapped_liability"].clause_id == "3"
    assert by_type["one_sided_indemnification"].clause_id == "4"
    assert by_type["ip_assignment_overreach"].clause_id == "5"
    assert by_type["non_compete"].clause_id == "6"


def test_every_citation_is_verifiable(sample_nda_path):
    """Show-your-work guardrail: each citation must appear in its clause."""
    _, clauses, findings = _review(sample_nda_path)
    by_id = {c.id: c for c in clauses}
    for f in findings:
        clause = by_id[f.clause_id]
        cite = f.citation.rstrip(".").rstrip("...")
        # The (possibly truncated) citation should be present in the clause.
        core = cite[:-3] if cite.endswith("...") else cite
        assert core[:40] in clause.text, f"citation not found in clause {f.clause_id}"


def test_every_finding_has_confidence_and_redline(sample_nda_path):
    _, _, findings = _review(sample_nda_path)
    assert findings
    for f in findings:
        assert f.confidence is not None
        assert f.suggested_redline.strip()
        assert f.rationale.strip()


def test_mutual_clause_not_flagged_as_uncapped():
    """A mutual, capped liability clause should not trigger uncapped_liability."""
    text = (
        "Each party's aggregate liability under this Agreement shall not exceed "
        "the fees paid in the preceding twelve months."
    )
    clause = Clause(
        id="X", heading="Liability", text=text, char_span=CharSpan(start=0, end=len(text))
    )
    findings = analyze_clause(clause, "Buyer", "US-DE")
    assert "uncapped_liability" not in {f.risk_type for f in findings}
