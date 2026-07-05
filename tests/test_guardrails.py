"""Guardrail tests (SPEC §14).

Every report carries the disclaimer; jurisdiction-specific conclusions are
withheld when jurisdiction is unknown; and there is no send capability anywhere
in the Phase-1 surface.
"""

import legal_agent
from legal_agent import review_contract
from legal_agent.agent.tools import render_markdown
from legal_agent.domain.jurisdictions import describe, is_known
from legal_agent.domain.schemas import DISCLAIMER


def test_report_always_contains_disclaimer(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer", jurisdiction="US-DE")
    assert report.disclaimer == DISCLAIMER
    assert "NOT legal advice" in report.disclaimer
    md = render_markdown(report)
    assert DISCLAIMER in md
    # Disclaimer must be visible near the top, not just buried at the end.
    assert md.index(DISCLAIMER) < len(md) // 2


def test_unknown_jurisdiction_is_withheld():
    assert not is_known(None)
    desc = describe(None)
    assert "withheld" in desc.lower()

    # An unrecognized jurisdiction is treated as unknown, not invented.
    assert not is_known("MARS-1")
    assert "unknown" in describe("MARS-1").lower()


def test_known_jurisdiction_recognized():
    assert is_known("US-CA")
    assert "California" in describe("US-CA")


def test_no_send_capability_exists():
    """The tool must never be able to transmit a document (SPEC §0, §10)."""
    forbidden = {"send", "email", "transmit", "file_with_court", "submit"}
    exported = set(dir(legal_agent))
    assert forbidden.isdisjoint(exported), "Phase 1 must expose no send capability"


def test_markdown_carries_draft_banner(sample_nda_path):
    report = review_contract(sample_nda_path, perspective="Buyer")
    md = render_markdown(report)
    assert "NOT LEGAL ADVICE" in md.upper()
