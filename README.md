# Legal Contract Review Agent

Decision-support software that ingests a contract, segments it into clauses, and
flags problematic clauses from a chosen party's perspective — with severity, a
plain-language rationale, a citation to the exact contract text, and a proposed
redline.

> ⚠️ **This is not a lawyer and does not give legal advice.** Every output is
> informational only, may be wrong, and must be reviewed by a qualified lawyer
> licensed in the relevant jurisdiction. The tool never sends anything — you
> review and act yourself. See [SPEC.md](SPEC.md) §0 for the full guardrails.

## Status — Phase 1 (contract flagger MVP)

The Phase-1 pipeline is complete and tested:

```
load_document → extract_clauses → analyze_clause → build_report
```

Parsing, segmentation, citation, and report assembly are **deterministic code**.
The model is used only for clause *judgement* (`analyze_clause`), and even that
falls back to a deterministic, offline heuristic analyzer so the tool works with
no API key.

Later phases (conversational agent loop, full taxonomy + RAG, case assessment,
document drafting) are described in [SPEC.md](SPEC.md) §12 and not yet built.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .            # core (TXT + offline heuristic analyzer)
# optional extras:
pip install -e ".[pdf]"     # PDF parsing (pdfplumber)
pip install -e ".[docx]"    # DOCX parsing (python-docx)
pip install -e ".[model]"   # Claude-backed analysis (anthropic)
pip install -e ".[all,dev]" # everything + tests
```

For model-backed analysis, copy `.env.example` to `.env` and set
`ANTHROPIC_API_KEY` (or export it in your shell).

## Use

```bash
# Offline heuristic analysis (default — free, no key, nothing leaves your machine):
legal-agent review contracts/sample_nda.pdf --side buyer --jurisdiction US-CA

# Machine-readable output:
legal-agent review contracts/sample_nda.txt --side vendor --format json -o report.json

# FREE local LLM analysis via Ollama (no API key — see "Analysis backends" below):
legal-agent review contracts/sample_nda.txt --side buyer -j US-CA --use-local

# Model-backed analysis with Claude (needs ANTHROPIC_API_KEY):
legal-agent review contracts/sample_nda.txt --side buyer -j US-CA --use-model
```

### Analysis backends

`analyze_clause` supports three backends; the default needs no key and no network:

| Backend | Flag | Cost | Key | Notes |
|---|---|---|---|---|
| Heuristic (default) | *(none)* | free | none | Deterministic pattern-matching against the taxonomy. Offline. |
| Local LLM | `--use-local` | free | none | A local [Ollama](https://ollama.com) model. Data stays on your machine — good for confidential contracts. |
| Claude | `--use-model` | paid | `ANTHROPIC_API_KEY` | Deepest, context-aware analysis via the Anthropic API. |

**No API key? Use one of the two free backends.** The heuristic default works
immediately. For a real LLM at no cost, use `--use-local` with Ollama:

```bash
# One-time setup:
#   1. Install Ollama:  https://ollama.com/download
#   2. Pull a model:    ollama pull llama3.1   (Ollama then serves on :11434)
legal-agent review contract.txt --side buyer -j US-CA --use-local
legal-agent review contract.txt --side buyer --use-local --local-model mistral
```

If Ollama isn't running, `--use-local` and `--use-model` (without a key) both
degrade gracefully to the free heuristic analyzer rather than failing.

`--side` is whose perspective to analyze from (e.g. `buyer`, `vendor`,
`employee`, `landlord`). `--jurisdiction` is optional; when omitted or
unrecognized, jurisdiction-specific conclusions are withheld rather than guessed.

As a library:

```python
from legal_agent import review_contract, render_markdown

report = review_contract("contract.txt", perspective="buyer", jurisdiction="US-CA")
print(render_markdown(report))
```

## What it checks

A taxonomy of common contract risks (see
`src/legal_agent/domain/clause_taxonomy.py`): uncapped/unbalanced liability,
one-sided indemnification, auto-renewal/evergreen terms, unfavorable
termination, governing law/venue, forced arbitration/class waiver, IP-assignment
overreach, overbroad non-compete, unilateral amendment, warranty disclaimers,
confidentiality asymmetry, unbalanced payment terms, assignment restrictions,
force-majeure gaps, missing SLAs, data-protection gaps, and ambiguous terms.
Each entry carries a default redline direction and a jurisdiction note where
enforceability varies.

## Data handling & privacy (SPEC §11)

- **Local by default.** Parsing, segmentation, citation, and report assembly all
  run locally with no network calls. The offline heuristic analyzer (and the
  `--use-local` Ollama backend) send nothing to any third party — the local
  backend runs the model on your own machine.
- **What leaves your machine, only with `--use-model`.** When you pass
  `--use-model`, the text of each clause (plus the taxonomy and your chosen
  perspective/jurisdiction) is sent to the Anthropic API for that clause's
  analysis. Nothing else — no file metadata, no full document — is transmitted,
  and results are not logged to any third party by this tool. `--use-local`
  keeps everything on your machine.
- **Never committed.** Contracts belong in a git-ignored `data/` directory and
  API keys in a git-ignored `.env`; both are excluded by `.gitignore`. Do not
  test on real client contracts — use synthetic or de-identified data.

## Project layout

```
src/legal_agent/
├── domain/        schemas.py (typed I/O), clause_taxonomy.py (§8), jurisdictions.py
├── io/            parsers.py (pdf/docx/txt), segmenter.py (text → clauses)
├── agent/
│   ├── system_prompt.py   role, guardrails, disclaimer
│   └── tools/             load_document, extract_clauses, analyze_clause, build_report
└── cli.py         `legal-agent review …`
templates/          demand_letter / statement_of_claim (Phase 5 stubs)
tests/              fixtures + parsing / segmentation / analysis / report / guardrail tests
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The suite covers parsing/citation faithfulness, clause segmentation, the planted
problems in the synthetic fixture (flagged at the expected severity), report
assembly, and the guardrails (disclaimer always present, unknown jurisdictions
withheld, no send capability).
