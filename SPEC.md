# Legal Contract Review Agent — Build Specification

**Purpose of this document.** This is a build spec for an agentic tool that
ingests contracts, flags problematic clauses, proposes redlines, assesses
whether there is a viable legal claim, and drafts documents (e.g. a demand
letter or statement of claim) that the user reviews and sends themselves. Build
it in phases, MVP first.

## 0. Read this first — scope, disclaimers, and guardrails

This tool touches legal analysis, so these constraints are product requirements,
not footnotes. Build them in from day one.

- This is decision-support software, not a lawyer. It never presents itself as a
  licensed attorney and never claims to give legal advice. Every substantive
  output carries a visible disclaimer: analysis is informational, may be wrong,
  and should be reviewed by a qualified lawyer in the relevant jurisdiction.
- Human-in-the-loop is mandatory. The agent drafts; the human decides and sends.
  The tool must never auto-send a demand letter, statement of claim, or any legal
  document. Sending is always an explicit, separate human action outside the
  agent.
- Jurisdiction-aware. Contract law, limitation periods, and pleading rules differ
  by country/state. The agent must know or ask which jurisdiction applies and
  must refuse to give jurisdiction-specific conclusions when it doesn't know.
- Show your work. Every flagged clause and every case-strength conclusion must
  cite the specific contract text and the reasoning, so a human can verify it. No
  unexplained verdicts.
- Calibrated confidence. Use explicit confidence levels (low / medium / high) and
  never manufacture false certainty about outcomes.
- Confidentiality. Contracts are sensitive. Default to local processing, don't
  log document contents to third parties, and make the data-handling model
  explicit to the user (see §11).
- Unauthorized-practice-of-law awareness. The tool assists the user with their
  own matter. It is not a service that dispenses legal advice to third parties.

## 1. What we're building

An agent that runs locally and walks a contract (or a dispute) through this
pipeline:

1. Ingest a contract from PDF / DOCX / plain text.
2. Segment it into clauses/sections with stable references.
3. Analyze each clause against a taxonomy of known risks (§8) from a chosen
   party's perspective.
4. Flag problematic clauses with severity, rationale, and citation to the exact
   text.
5. Redline — propose corrected/safer clause language.
6. Report — produce a structured risk report.
7. Assess a case (optional, dispute mode) — evaluate whether there is a viable
   claim, its elements, strength, and limitations (§9).
8. Draft — on request, produce a demand letter or a statement-of-claim draft for
   the user to review, edit, and send (§10).

## 2. Design principles

- Build from scratch, understand the loop: reason → request a tool → run the
  tool → feed the result back → repeat until done.
- The model requests, our code executes.
- Deterministic where it matters. Parsing, clause segmentation, citation, and
  document assembly are deterministic code. Use the model for judgment.
- Composable tools. Each capability is a discrete tool with typed I/O.
- MVP first. Phase 1 is a working contract-flagger.

## 6. The tools

- `load_document(path) -> Document` — parse PDF/DOCX/TXT into normalized text plus
  character spans; return metadata.
- `extract_clauses(document) -> list[Clause]` — segment into clauses with stable
  refs (`id`, `heading`, `text`, `char_span`, `page`).
- `analyze_clause(clause, perspective, jurisdiction) -> list[Finding]` — the
  judgment step. Each `Finding`: `risk_type`, `severity`, `rationale`, `citation`,
  `suggested_redline`, `confidence`.
- `build_report(findings, document) -> Report` — deterministically assemble
  findings sorted by severity, with an executive summary, redline appendix, and
  the mandatory disclaimer. Output JSON and Markdown.
- `assess_case(narrative, documents, jurisdiction) -> CaseAssessment` — dispute
  mode (§9). *(Phase 4.)*
- `draft_document(kind, matter, jurisdiction) -> Draft` — produce a draft (never
  sent) of a demand letter or statement of claim. *(Phase 5.)*

## 8. Clause risk taxonomy

Uncapped/unbalanced liability; one-sided indemnification; auto-renewal/evergreen;
unfavorable termination; governing law/venue; forced arbitration/class waiver; IP
assignment overreach; overbroad non-compete/non-solicit; unilateral amendment;
warranty disclaimers/"as-is"; confidentiality asymmetry; payment terms; assignment
restrictions; force majeure gaps; missing SLA/remedies; data protection/privacy
gaps; ambiguous/undefined terms. Each carries a jurisdiction note where
enforceability varies. Implemented in `domain/clause_taxonomy.py`.

## 9. Case-assessment module (dispute mode) — Phase 4

Elements-based method: classify claim types → list legal elements per
jurisdiction → map facts to elements → identify gaps → strength band with
confidence → limitation-period flag → next steps. Always ends by recommending
review with a qualified lawyer; never tells the user they will win.

## 10. Document drafting + the "send it yourself" step — Phase 5

`draft_document` produces a draft only (demand letter, statement of claim). Every
draft includes a review checklist and a prominent "draft only — review with a
qualified lawyer before sending or filing" banner. No send integration; the human
transmits it.

## 11. Data handling & privacy

- Process documents locally; only clause text needed for analysis is sent to the
  model API. Make this explicit to the user.
- Never commit contracts, keys, or client data to the repo. Use `.env` for
  secrets and a git-ignored `data/` dir for documents.
- Document the data flow in the README so a user knows exactly what leaves their
  machine.

## 12. Build phases

- **Phase 1 — Contract flagger MVP.** `load_document` → `extract_clauses` →
  `analyze_clause` (subset of taxonomy) → `build_report`. CLI:
  `legal-agent review <file> --side buyer --jurisdiction <x>`. **← current phase.**
- Phase 2 — Conversational agent (Claude Agent SDK loop + REPL).
- Phase 3 — Full taxonomy + redline quality + optional RAG.
- Phase 4 — Case assessment (`assess_case`).
- Phase 5 — Drafting (`draft_document`).
- Phase 6 — Polish (DOCX/PDF export, matter ledger, batch review, eval harness).

## 13. Setup & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env            # add ANTHROPIC_API_KEY (only for --use-model)
legal-agent review contracts/sample_nda.pdf --side buyer --jurisdiction "US-CA"
```

## 14. Testing & evaluation

- Fixtures: synthetic contracts with known planted problems; assert the tool
  flags them at the right severity.
- Parsing tests: PDF/DOCX/TXT normalize correctly; citations point to the right
  spans.
- Guardrail tests: every report contains the disclaimer; `assess_case`/drafting
  refuse jurisdiction-specific conclusions when jurisdiction is unknown; drafting
  exposes no send path.
- Regression eval: a labeled set of clauses with expected `risk_type`.
- Never test on real client contracts.

## 15. Notes

1. Start with Phase 1 only.
2. Define pydantic schemas in `domain/schemas.py` first — the contract between
   tools.
3. Keep parsing/segmentation/citation deterministic; use the model only for
   `analyze_clause`, `assess_case`, and prose in `draft_document`.
4. Put the disclaimer and human-in-the-loop rules in the system prompt and in
   report/draft assembly so they can't be skipped.
5. Confirm the Claude Agent SDK API against current docs before writing the loop.
6. Write a test alongside each tool.
7. Ask the user for target jurisdiction and default perspective rather than
   guessing.

---

*This document defines software that assists a user with their own legal
matters. It is not legal advice, and the tool it describes must consistently tell
its users the same.*
