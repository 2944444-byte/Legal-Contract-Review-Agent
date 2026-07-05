"""Deterministic clause segmentation: text -> clauses with stable refs.

Segmentation is deterministic (SPEC §2, §15.3). We use structural cues —
numbered sections (``1.``, ``1.1``, ``12.3.4``), ``Section N`` / ``Article N``
headings, and short ALL-CAPS heading lines — to split the document at clause
boundaries. Each clause carries a stable id, its heading, the exact text, a
character span into the normalized document text, and a page number.

If no structural markers are found (a messy document), we fall back to
paragraph-based segmentation so the pipeline still produces citable units.
A model-assisted segmenter is a Phase 3 enhancement; the boundaries here stay
deterministic.
"""

from __future__ import annotations

import re

from ..domain.schemas import CharSpan, Clause, Document

# A line that begins a numbered clause, e.g. "1.", "1.1", "12.3 Term", or a
# "Section 4" / "Article II" heading. Anchored to the start of a line.
_NUMBERED = re.compile(
    r"^[ \t]*(?P<marker>(?:section|article|clause)\s+[0-9ivxlcIVXLC]+|[0-9]+(?:\.[0-9]+)*)\.?"
    r"(?P<rest>[ \t)\-–—:.].*)?$",
    re.IGNORECASE,
)

# A short, mostly-uppercase heading line (e.g. "CONFIDENTIALITY").
_CAPS_HEADING = re.compile(r"^[ \t]*[A-Z][A-Z0-9 ,&/'\-]{2,60}$")


def _is_heading_line(line: str) -> tuple[bool, str | None]:
    """Return ``(is_heading, marker)`` for a line."""
    m = _NUMBERED.match(line)
    if m:
        return True, m.group("marker").strip()
    stripped = line.strip()
    if _CAPS_HEADING.match(line) and len(stripped.split()) <= 8:
        # Avoid treating a normal sentence in caps as a heading.
        if not stripped.endswith((".", ";", ",")):
            return True, stripped
    return False, None


def _line_offsets(text: str) -> list[int]:
    """Character offset at which each line starts."""
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def segment(document: Document) -> list[Clause]:
    """Split a document into clauses with stable references and spans."""
    text = document.text
    lines = text.split("\n")
    line_starts = _line_offsets(text)

    # Find heading line indices and their markers.
    boundaries: list[tuple[int, str | None]] = []
    for idx, line in enumerate(lines):
        is_head, marker = _is_heading_line(line)
        if is_head:
            boundaries.append((idx, marker))

    if not boundaries:
        return _segment_by_paragraph(document, text)

    clauses: list[Clause] = []
    seen_ids: dict[str, int] = {}
    for n, (line_idx, marker) in enumerate(boundaries):
        start = line_starts[line_idx]
        if n + 1 < len(boundaries):
            end = line_starts[boundaries[n + 1][0]]
        else:
            end = len(text)
        span_text = text[start:end].strip()
        if not span_text:
            continue
        heading = lines[line_idx].strip()
        clause_id = _stable_id(marker, n, seen_ids)
        # Tighten the span to the stripped text so citations are exact.
        lead = len(text[start:end]) - len(text[start:end].lstrip())
        real_start = start + lead
        real_end = real_start + len(span_text)
        clauses.append(
            Clause(
                id=clause_id,
                heading=heading or None,
                text=span_text,
                char_span=CharSpan(start=real_start, end=real_end),
                page=document.page_for_offset(real_start),
            )
        )
    return clauses


def _segment_by_paragraph(document: Document, text: str) -> list[Clause]:
    """Fallback: split on blank lines into paragraph-sized clauses."""
    clauses: list[Clause] = []
    offset = 0
    n = 0
    for block in re.split(r"\n[ \t]*\n", text):
        stripped = block.strip()
        block_start = text.find(block, offset)
        offset = block_start + len(block)
        if not stripped:
            continue
        lead = len(block) - len(block.lstrip())
        real_start = block_start + lead
        real_end = real_start + len(stripped)
        n += 1
        clauses.append(
            Clause(
                id=f"P{n}",
                heading=None,
                text=stripped,
                char_span=CharSpan(start=real_start, end=real_end),
                page=document.page_for_offset(real_start),
            )
        )
    return clauses


def _stable_id(marker: str | None, index: int, seen: dict[str, int]) -> str:
    if not marker:
        return f"C{index + 1}"
    base = re.sub(r"\s+", " ", marker).strip()
    if base in seen:
        seen[base] += 1
        return f"{base} ({seen[base]})"
    seen[base] = 1
    return base
