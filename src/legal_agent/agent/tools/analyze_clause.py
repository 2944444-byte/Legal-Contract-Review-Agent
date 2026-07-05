"""Tool: analyze_clause(clause, perspective, jurisdiction) -> list[Finding].

This is the judgment step (SPEC §6). Two analyzers are provided:

* :func:`heuristic_analyze` — deterministic, offline, pattern-based against the
  taxonomy. This is the default and what the tests target: it needs no API key
  and produces reproducible output.
* :class:`ClaudeAnalyzer` — model-backed judgement via the Anthropic API with
  structured (pydantic) output. Used when an API key is available and the caller
  opts into it.

Both return zero or more :class:`Finding` objects citing the exact clause text.
Only the model call involves the LLM; everything else stays deterministic.
"""

from __future__ import annotations

import os
import re
from typing import Protocol

from ...domain.clause_taxonomy import TAXONOMY, RiskType
from ...domain.schemas import Clause, Confidence, Finding, Severity
from ..system_prompt import ANALYST_SYSTEM_PROMPT

MODEL = "claude-opus-4-8"


class Analyzer(Protocol):
    def __call__(
        self, clause: Clause, perspective: str, jurisdiction: str | None
    ) -> list[Finding]: ...


# ---------------------------------------------------------------------------
# Deterministic analyzer
# ---------------------------------------------------------------------------
def _first_match_sentence(text: str, patterns: tuple[str, ...]) -> str:
    """Return the sentence that first matches any pattern, for citation."""
    low = text.lower()
    best: int | None = None
    for p in patterns:
        m = re.search(p, low)
        if m and (best is None or m.start() < best):
            best = m.start()
    if best is None:
        snippet = text.strip()
    else:
        # Expand to sentence boundaries around the match.
        start = text.rfind(".", 0, best)
        start = 0 if start == -1 else start + 1
        end = text.find(".", best)
        end = len(text) if end == -1 else end + 1
        snippet = text[start:end].strip()
    # Keep citations reasonably short.
    return snippet if len(snippet) <= 300 else snippet[:297].rstrip() + "..."


def _finding_for(
    clause: Clause, risk: RiskType, perspective: str
) -> Finding:
    party = perspective.strip() or "the analyzed party"
    return Finding(
        risk_type=risk.key,
        severity=risk.default_severity,
        rationale=risk.why_it_hurts.format(party=party)
        + (f" Jurisdiction note: {risk.jurisdiction_note}" if risk.jurisdiction_note else ""),
        clause_id=clause.id,
        citation=_first_match_sentence(clause.text, risk.patterns),
        suggested_redline=risk.default_redline,
        # Pattern matching is indicative, not conclusive -> medium confidence.
        confidence=Confidence.MEDIUM,
    )


def heuristic_analyze(
    clause: Clause, perspective: str, jurisdiction: str | None = None
) -> list[Finding]:
    """Deterministic, pattern-based analysis against the taxonomy."""
    findings: list[Finding] = []
    for risk in TAXONOMY.values():
        if risk.patterns and risk.matches(clause.text):
            findings.append(_finding_for(clause, risk, perspective))
    return findings


# ---------------------------------------------------------------------------
# Model-backed analyzer
# ---------------------------------------------------------------------------
class _ModelFindings:
    """Lazily-built pydantic schema for the model's structured output."""

    _cached = None

    @classmethod
    def schema(cls):
        if cls._cached is not None:
            return cls._cached
        from pydantic import BaseModel, Field

        risk_keys = list(TAXONOMY.keys())

        class _Finding(BaseModel):
            risk_type: str = Field(description="One of: " + ", ".join(risk_keys))
            severity: Severity
            rationale: str
            citation: str = Field(description="Exact quoted text from the clause")
            suggested_redline: str
            confidence: Confidence

        class _FindingList(BaseModel):
            findings: list[_Finding]

        cls._cached = _FindingList
        return cls._cached


class ClaudeAnalyzer:
    """Model-backed clause analysis using the Anthropic API.

    Falls back to :func:`heuristic_analyze` on any API/import error so the
    pipeline never hard-fails just because the model is unavailable.
    """

    def __init__(self, model: str = MODEL, api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic  # imported lazily

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def __call__(
        self, clause: Clause, perspective: str, jurisdiction: str | None
    ) -> list[Finding]:
        try:
            return self._analyze(clause, perspective, jurisdiction)
        except Exception:
            # Never let a model failure break the pipeline; degrade gracefully.
            return heuristic_analyze(clause, perspective, jurisdiction)

    def _analyze(
        self, clause: Clause, perspective: str, jurisdiction: str | None
    ) -> list[Finding]:
        client = self._get_client()
        schema_model = _ModelFindings.schema()
        user = _user_prompt(clause, perspective, jurisdiction)
        response = client.messages.parse(
            model=self.model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=ANALYST_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
            output_format=schema_model,
        )
        parsed = response.parsed_output
        if parsed is None:
            return heuristic_analyze(clause, perspective, jurisdiction)
        findings: list[Finding] = []
        for f in parsed.findings:
            findings.append(
                Finding(
                    risk_type=f.risk_type,
                    severity=f.severity,
                    rationale=f.rationale,
                    clause_id=clause.id,
                    citation=f.citation,
                    suggested_redline=f.suggested_redline,
                    confidence=f.confidence,
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Shared prompt / schema helpers (used by both model backends)
# ---------------------------------------------------------------------------
def _taxonomy_lines() -> str:
    return "\n".join(
        f"- {r.key}: {r.name} — {r.description}" for r in TAXONOMY.values()
    )


def _user_prompt(clause: Clause, perspective: str, jurisdiction: str | None) -> str:
    juris = jurisdiction or "UNKNOWN (withhold jurisdiction-specific conclusions)"
    return (
        f"Analyze the following clause from the perspective of: {perspective}.\n"
        f"Jurisdiction: {juris}.\n\n"
        f"Risk taxonomy (use these risk_type keys):\n{_taxonomy_lines()}\n\n"
        f"Clause id: {clause.id}\n"
        f"Clause heading: {clause.heading or '(none)'}\n"
        f"Clause text:\n\"\"\"\n{clause.text}\n\"\"\"\n\n"
        "Return only genuine issues for this party, each citing exact clause "
        "text. If there are no issues, return an empty findings list."
    )


def _findings_json_schema() -> dict:
    """A plain JSON schema for the findings list (for non-pydantic backends)."""
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk_type": {"type": "string", "enum": list(TAXONOMY.keys())},
                        "severity": {"type": "string", "enum": [s.value for s in Severity]},
                        "rationale": {"type": "string"},
                        "citation": {"type": "string"},
                        "suggested_redline": {"type": "string"},
                        "confidence": {
                            "type": "string",
                            "enum": [c.value for c in Confidence],
                        },
                    },
                    "required": [
                        "risk_type",
                        "severity",
                        "rationale",
                        "citation",
                        "suggested_redline",
                        "confidence",
                    ],
                },
            }
        },
        "required": ["findings"],
    }


def _coerce_findings(raw_findings: list[dict], clause: Clause) -> list[Finding]:
    """Turn raw model dicts into validated Findings, skipping malformed ones."""
    out: list[Finding] = []
    for f in raw_findings:
        try:
            out.append(
                Finding(
                    risk_type=str(f["risk_type"]),
                    severity=Severity(str(f["severity"]).lower()),
                    rationale=str(f.get("rationale", "")),
                    clause_id=clause.id,
                    citation=str(f.get("citation", "")),
                    suggested_redline=str(f.get("suggested_redline", "")),
                    confidence=Confidence(str(f.get("confidence", "low")).lower()),
                )
            )
        except (KeyError, ValueError):
            continue  # skip a malformed finding rather than fail the clause
    return out


# ---------------------------------------------------------------------------
# Local model analyzer (Ollama / any OpenAI-free, keyless local server)
# ---------------------------------------------------------------------------
DEFAULT_LOCAL_MODEL = "llama3.1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class LocalModelAnalyzer:
    """Clause analysis via a local Ollama server — free and keyless.

    Talks to Ollama's ``/api/chat`` endpoint (default http://localhost:11434)
    using only the standard library, and asks for JSON matching the findings
    schema. Nothing leaves the machine, which suits confidential contracts
    (SPEC §11). Falls back to :func:`heuristic_analyze` if the server is
    unreachable or returns something unusable, so the pipeline never breaks.

    Setup (one time):
        1. Install Ollama: https://ollama.com/download
        2. Pull a model:   ollama pull llama3.1
        3. Ollama serves automatically on http://localhost:11434
    """

    def __init__(self, model: str = DEFAULT_LOCAL_MODEL, base_url: str | None = None):
        self.model = model
        raw = base_url or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_URL
        if not raw.startswith("http"):
            raw = "http://" + raw
        self.base_url = raw.rstrip("/")

    def __call__(
        self, clause: Clause, perspective: str, jurisdiction: str | None
    ) -> list[Finding]:
        try:
            return self._analyze(clause, perspective, jurisdiction)
        except Exception:
            return heuristic_analyze(clause, perspective, jurisdiction)

    def _analyze(
        self, clause: Clause, perspective: str, jurisdiction: str | None
    ) -> list[Finding]:
        import json
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(clause, perspective, jurisdiction)},
            ],
            "format": _findings_json_schema(),
            "stream": False,
            "options": {"temperature": 0},
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("message", {}).get("content", "")
        parsed = json.loads(content)
        return _coerce_findings(parsed.get("findings", []), clause)


def get_analyzer(
    backend: str = "heuristic",
    api_key: str | None = None,
    local_model: str = DEFAULT_LOCAL_MODEL,
    base_url: str | None = None,
    prefer_model: bool | None = None,
) -> Analyzer:
    """Pick an analyzer by backend name.

    backends:
      * ``"heuristic"`` — deterministic, offline, free, no key (default).
      * ``"local"``     — local Ollama model, free, no key (data stays local).
      * ``"claude"``    — Anthropic API (needs ANTHROPIC_API_KEY).

    ``prefer_model=True`` is accepted for backward compatibility and maps to
    the ``"claude"`` backend.
    """
    if prefer_model:
        backend = "claude"
    backend = (backend or "heuristic").lower()

    if backend == "local":
        return LocalModelAnalyzer(model=local_model, base_url=base_url)
    if backend == "claude":
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return ClaudeAnalyzer(api_key=key)
        # No key -> degrade to the free offline analyzer rather than crash.
        return heuristic_analyze
    return heuristic_analyze


def analyze_clause(
    clause: Clause,
    perspective: str,
    jurisdiction: str | None = None,
    analyzer: Analyzer | None = None,
) -> list[Finding]:
    """Analyze a single clause and return zero or more findings."""
    analyzer = analyzer or heuristic_analyze
    return analyzer(clause, perspective, jurisdiction)
