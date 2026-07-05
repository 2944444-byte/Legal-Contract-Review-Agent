"""Parsing tests: TXT normalizes correctly and citation offsets are exact."""

import pytest

from legal_agent.io.parsers import UnsupportedFormatError, parse_document


def test_parse_txt_basic(sample_nda_path):
    doc = parse_document(sample_nda_path)
    assert doc.source_format == "txt"
    assert doc.page_count == 1
    assert doc.page_starts == [0]
    assert "MASTER SERVICES" in doc.text
    assert doc.title.startswith("MASTER SERVICES")


def test_parse_normalizes_line_endings(tmp_path):
    p = tmp_path / "crlf.txt"
    p.write_bytes(b"Line one\r\nLine two\r\n")
    doc = parse_document(str(p))
    assert "\r" not in doc.text
    assert doc.text == "Line one\nLine two\n"


def test_char_span_offsets_are_faithful(sample_nda_path):
    """A slice of the normalized text must return the exact original substring."""
    doc = parse_document(sample_nda_path)
    idx = doc.text.index("binding arbitration")
    assert doc.text[idx : idx + len("binding arbitration")] == "binding arbitration"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_document("/nonexistent/contract.txt")


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / "contract.rtf"
    p.write_text("hello")
    with pytest.raises(UnsupportedFormatError):
        parse_document(str(p))
