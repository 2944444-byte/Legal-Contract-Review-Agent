"""Tool: extract_clauses(document) -> list[Clause] (SPEC §6)."""

from __future__ import annotations

from ...domain.schemas import Clause, Document
from ...io.segmenter import segment


def extract_clauses(document: Document) -> list[Clause]:
    """Segment a document into clauses with stable references and spans."""
    return segment(document)
