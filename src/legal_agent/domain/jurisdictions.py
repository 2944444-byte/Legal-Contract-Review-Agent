"""Jurisdiction registry (SPEC §0 jurisdiction-awareness).

The tool must know or ask which jurisdiction applies, and must refuse to give
jurisdiction-specific conclusions when it does not know. This module is a
minimal registry of what we know / don't know, plus normalization helpers.

It is deliberately small in Phase 1: it records recognized jurisdiction codes
and short notes, and flags everything else as "unknown" so downstream code can
withhold jurisdiction-specific conclusions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Jurisdiction:
    code: str
    name: str
    note: str


# A small, non-exhaustive registry. The point of Phase 1 is not legal
# completeness but honesty about what we know vs. don't.
_REGISTRY: dict[str, Jurisdiction] = {
    "US-CA": Jurisdiction(
        "US-CA",
        "United States — California",
        "Non-competes are generally void; strong consumer/privacy (CCPA/CPRA) rules.",
    ),
    "US-NY": Jurisdiction(
        "US-NY",
        "United States — New York",
        "Common commercial-contract choice of law; enforces reasonable restrictive covenants.",
    ),
    "US-DE": Jurisdiction(
        "US-DE",
        "United States — Delaware",
        "Common corporate/commercial choice of law; predictable contract enforcement.",
    ),
    "US": Jurisdiction(
        "US",
        "United States (unspecified state)",
        "State law governs most contract terms; specify a state for precise conclusions.",
    ),
    "UK": Jurisdiction(
        "UK",
        "United Kingdom (England & Wales)",
        "UCTA/Consumer Rights Act limit exclusions; restrictive covenants must be reasonable.",
    ),
    "EU": Jurisdiction(
        "EU",
        "European Union",
        "GDPR governs personal data; unfair-terms rules apply to consumer contracts.",
    ),
    "CA": Jurisdiction(
        "CA",
        "Canada",
        "Provincial law governs; specify a province for precise conclusions.",
    ),
    "AU": Jurisdiction(
        "AU",
        "Australia",
        "Australian Consumer Law limits unfair terms and warranty exclusions.",
    ),
}


def normalize(raw: str | None) -> str | None:
    """Normalize a user-supplied jurisdiction string to a registry code.

    Returns ``None`` when nothing is supplied. Returns the raw (upper-cased)
    string when it is not recognized, so callers can still surface it while
    treating it as unknown via :func:`is_known`.
    """
    if not raw:
        return None
    key = raw.strip().upper().replace("_", "-").replace(" ", "-")
    if key in _REGISTRY:
        return key
    # Accept a bare country prefix, e.g. "US-TX" -> known-country "US".
    prefix = key.split("-", 1)[0]
    if prefix in _REGISTRY:
        return key  # keep the specific code but it will read as unknown-state
    return key


def is_known(code: str | None) -> bool:
    return bool(code) and code in _REGISTRY


def describe(code: str | None) -> str:
    if not code:
        return (
            "No jurisdiction specified. Jurisdiction-specific conclusions are "
            "withheld; findings reflect general contract principles only."
        )
    if code in _REGISTRY:
        j = _REGISTRY[code]
        return f"{j.name} ({j.code}): {j.note}"
    return (
        f"'{code}' is not in the jurisdiction registry. Treating as UNKNOWN — "
        "jurisdiction-specific conclusions are withheld."
    )
