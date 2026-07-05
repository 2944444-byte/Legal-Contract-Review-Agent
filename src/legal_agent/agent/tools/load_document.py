"""Tool: load_document(path) -> Document (SPEC §6)."""

from __future__ import annotations

from ...domain.schemas import Document
from ...io.parsers import parse_document


def load_document(path: str) -> Document:
    """Parse a PDF/DOCX/TXT contract into a normalized :class:`Document`."""
    return parse_document(path)
