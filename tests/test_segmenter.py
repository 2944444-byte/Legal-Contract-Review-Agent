"""Segmentation tests: clauses get stable refs and citations point at spans."""

from legal_agent.io.parsers import parse_document
from legal_agent.io.segmenter import segment


def test_segments_numbered_clauses(sample_nda_path):
    doc = parse_document(sample_nda_path)
    clauses = segment(doc)
    ids = [c.id for c in clauses]
    # The fixture has numbered sections 1..11.
    for n in range(1, 12):
        assert str(n) in ids, f"missing clause {n}; got {ids}"


def test_clause_spans_match_document_text(sample_nda_path):
    doc = parse_document(doc_path := sample_nda_path)
    clauses = segment(doc)
    for c in clauses:
        # The stored text must equal the exact slice of the document text.
        assert c.char_span.slice(doc.text) == c.text


def test_clause_headings_captured(sample_nda_path):
    doc = parse_document(sample_nda_path)
    clauses = segment(doc)
    by_id = {c.id: c for c in clauses}
    assert "Non-Compet" in by_id["6"].heading
    assert "Confidential" in by_id["7"].heading


def test_paragraph_fallback_when_no_markers():
    from legal_agent.domain.schemas import Document

    text = "First paragraph of terms.\n\nSecond paragraph of terms."
    doc = Document(path="mem.txt", text=text, source_format="txt")
    clauses = segment(doc)
    assert len(clauses) == 2
    assert clauses[0].id == "P1"
    assert clauses[0].char_span.slice(text) == "First paragraph of terms."
