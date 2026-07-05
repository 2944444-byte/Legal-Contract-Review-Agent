"""Analyzer backend selection and graceful degradation."""

from legal_agent.agent.tools import (
    ClaudeAnalyzer,
    LocalModelAnalyzer,
    get_analyzer,
    heuristic_analyze,
)
from legal_agent.agent.tools.analyze_clause import _findings_json_schema
from legal_agent.domain.clause_taxonomy import TAXONOMY
from legal_agent.domain.schemas import CharSpan, Clause


def test_default_backend_is_heuristic():
    assert get_analyzer() is heuristic_analyze
    assert get_analyzer("heuristic") is heuristic_analyze


def test_local_backend_returns_local_analyzer():
    a = get_analyzer("local", local_model="mistral")
    assert isinstance(a, LocalModelAnalyzer)
    assert a.model == "mistral"


def test_claude_backend_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert get_analyzer("claude") is heuristic_analyze


def test_claude_backend_with_key_returns_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(get_analyzer("claude"), ClaudeAnalyzer)


def test_prefer_model_maps_to_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert isinstance(get_analyzer(prefer_model=True), ClaudeAnalyzer)


def test_local_analyzer_degrades_when_server_unreachable():
    """An unreachable Ollama server must fall back, never raise."""
    # Point at a port nothing is listening on.
    analyzer = LocalModelAnalyzer(base_url="http://127.0.0.1:1")
    clause = Clause(
        id="1",
        heading="Liability",
        text="Buyer shall be liable for any and all damages, without limitation of liability.",
        char_span=CharSpan(start=0, end=80),
    )
    findings = analyzer(clause, "Buyer", "US-CA")
    # Falls back to the heuristic, which flags uncapped liability.
    assert "uncapped_liability" in {f.risk_type for f in findings}


def test_findings_schema_enumerates_taxonomy():
    schema = _findings_json_schema()
    props = schema["properties"]["findings"]["items"]["properties"]
    assert set(props["risk_type"]["enum"]) == set(TAXONOMY.keys())
