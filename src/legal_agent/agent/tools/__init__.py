"""The six composable tools (SPEC §6). Phase 1 ships the first four."""

from __future__ import annotations

from .analyze_clause import (
    ClaudeAnalyzer,
    LocalModelAnalyzer,
    analyze_clause,
    get_analyzer,
    heuristic_analyze,
)
from .build_report import build_report, render_markdown
from .extract_clauses import extract_clauses
from .load_document import load_document

__all__ = [
    "load_document",
    "extract_clauses",
    "analyze_clause",
    "heuristic_analyze",
    "ClaudeAnalyzer",
    "LocalModelAnalyzer",
    "get_analyzer",
    "build_report",
    "render_markdown",
]
