"""The clause risk catalog (SPEC §8).

Each :class:`RiskType` records what the risk is, why it can hurt the named
party, a default redline direction, a jurisdiction note where enforceability
varies, and lightweight detection patterns used by the deterministic
(offline) analyzer. The model-backed analyzer uses the same catalog as its
vocabulary of ``risk_type`` values.

The taxonomy is intentionally data, not code, so it can be expanded over time
(SPEC Phase 3) without touching the pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schemas import Severity


@dataclass(frozen=True)
class RiskType:
    key: str
    name: str
    description: str
    why_it_hurts: str
    default_redline: str
    default_severity: Severity
    jurisdiction_note: str = ""
    # Case-insensitive regex fragments; a clause matching any of these is a
    # candidate for this risk in the deterministic analyzer.
    patterns: tuple[str, ...] = field(default_factory=tuple)
    # Regexes that, if present, indicate the protection already exists and the
    # risk is mitigated (used to reduce false positives, e.g. a liability cap).
    mitigating_patterns: tuple[str, ...] = field(default_factory=tuple)

    def matches(self, text: str) -> bool:
        low = text.lower()
        if not any(re.search(p, low) for p in self.patterns):
            return False
        if any(re.search(m, low) for m in self.mitigating_patterns):
            return False
        return True


TAXONOMY: dict[str, RiskType] = {
    r.key: r
    for r in [
        RiskType(
            key="uncapped_liability",
            name="Uncapped / unbalanced liability",
            description=(
                "No limitation-of-liability cap, or a cap that only protects "
                "the counterparty."
            ),
            why_it_hurts=(
                "Exposes {party} to unlimited or one-sided financial liability."
            ),
            default_redline=(
                "Add a mutual, reasonable limitation-of-liability cap (e.g. "
                "fees paid in the preceding 12 months) applying to both parties."
            ),
            default_severity=Severity.HIGH,
            jurisdiction_note=(
                "Enforceability of liability caps and exclusions of "
                "consequential damages varies; some jurisdictions bar capping "
                "liability for gross negligence or willful misconduct."
            ),
            patterns=(
                r"unlimited liabilit",
                r"without limitation of liabilit",
                r"no (?:cap|limit) on (?:its )?liabilit",
                r"liable for (?:any and )?all (?:damages|losses)",
            ),
            mitigating_patterns=(
                r"aggregate liability .{0,40}(?:shall not exceed|limited to|capped)",
                r"total liability .{0,40}(?:shall not exceed|limited to|capped)",
            ),
        ),
        RiskType(
            key="one_sided_indemnification",
            name="One-sided indemnification",
            description=(
                "You indemnify them broadly; they indemnify you narrowly or "
                "not at all."
            ),
            why_it_hurts=(
                "Shifts the cost of third-party claims disproportionately onto "
                "{party}."
            ),
            default_redline=(
                "Make indemnification mutual and scope-limited to each party's "
                "own breach, negligence, or IP infringement."
            ),
            default_severity=Severity.HIGH,
            jurisdiction_note=(
                "Indemnity for a party's own negligence must often be "
                "'clear and conspicuous' to be enforceable."
            ),
            patterns=(
                r"shall indemnify",
                r"indemnif(?:y|ies|ication)",
                r"hold harmless",
            ),
            mitigating_patterns=(
                r"each party (?:shall|will) indemnif",
                r"mutual(?:ly)? indemnif",
            ),
        ),
        RiskType(
            key="auto_renewal",
            name="Auto-renewal / evergreen term",
            description=(
                "Renews automatically with a short or onerous opt-out window."
            ),
            why_it_hurts=(
                "{party} can be locked into another term by missing a narrow "
                "notice window."
            ),
            default_redline=(
                "Add a clear, reasonable non-renewal notice period (e.g. 30 "
                "days) and an easy right to terminate for convenience."
            ),
            default_severity=Severity.MEDIUM,
            jurisdiction_note=(
                "Some jurisdictions require conspicuous notice of automatic "
                "renewal for consumer or small-business contracts."
            ),
            patterns=(
                r"automatically renew",
                r"auto-?renew",
                r"evergreen",
                r"renew(?:s|ed)? for (?:successive|additional) (?:term|period)",
            ),
        ),
        RiskType(
            key="unfavorable_termination",
            name="Unfavorable termination rights",
            description=(
                "They can exit freely; you are locked in or penalized on exit."
            ),
            why_it_hurts="{party} lacks a symmetric or convenient way to exit.",
            default_redline=(
                "Provide symmetric termination-for-convenience and "
                "termination-for-cause rights with equal notice periods."
            ),
            default_severity=Severity.MEDIUM,
            patterns=(
                r"terminate (?:this agreement )?for convenience",
                r"sole discretion to terminate",
                r"early termination (?:fee|penalt|charge)",
            ),
        ),
        RiskType(
            key="governing_law_venue",
            name="Governing law / venue",
            description="Inconvenient or counterparty-favorable jurisdiction.",
            why_it_hurts=(
                "Forces {party} to litigate in a distant or unfavorable forum."
            ),
            default_redline=(
                "Select a neutral governing law/venue, or {party}'s home "
                "jurisdiction."
            ),
            default_severity=Severity.LOW,
            jurisdiction_note=(
                "Forum-selection and choice-of-law clauses are generally "
                "enforced but may be overridden by mandatory local law."
            ),
            patterns=(
                r"governed by the laws of",
                r"exclusive jurisdiction",
                r"venue (?:shall|will) (?:be|lie)",
                r"submit to the (?:exclusive )?jurisdiction",
            ),
        ),
        RiskType(
            key="forced_arbitration",
            name="Forced arbitration / class waiver",
            description="May strip meaningful remedies or a day in court.",
            why_it_hurts=(
                "Limits {party}'s remedies and ability to pursue class relief."
            ),
            default_redline=(
                "Flag for review; consider carve-outs (injunctive relief, small "
                "claims) or mutual, balanced arbitration terms."
            ),
            default_severity=Severity.MEDIUM,
            jurisdiction_note=(
                "Arbitration and class-action waivers are broadly enforceable "
                "in the US under the FAA but restricted in some jurisdictions "
                "and for certain claims."
            ),
            patterns=(
                r"binding arbitration",
                r"waive.{0,30}(?:class action|jury trial)",
                r"class action waiver",
            ),
        ),
        RiskType(
            key="ip_assignment_overreach",
            name="IP assignment overreach",
            description="Assigns more IP than the deal requires.",
            why_it_hurts=(
                "{party} may lose ownership of background or unrelated IP."
            ),
            default_redline=(
                "Narrow assignment to the specific deliverables; license "
                "(rather than assign) background IP where possible."
            ),
            default_severity=Severity.HIGH,
            patterns=(
                r"assigns? all (?:right, title|intellectual property)",
                r"all work product .{0,40}(?:belong|owned|assigned)",
                r"hereby assigns",
            ),
            mitigating_patterns=(r"background (?:ip|intellectual property) .{0,40}retain",),
        ),
        RiskType(
            key="non_compete",
            name="Overbroad non-compete / non-solicit",
            description="Unreasonable scope, duration, or geography.",
            why_it_hurts="Restricts {party}'s future business or employment.",
            default_redline=(
                "Narrow scope, duration, and geography to what is reasonable "
                "and necessary; flag enforceability by jurisdiction."
            ),
            default_severity=Severity.HIGH,
            jurisdiction_note=(
                "Non-competes are unenforceable or heavily restricted in some "
                "jurisdictions (e.g. California) and for many employees."
            ),
            patterns=(
                r"non-?compete",
                r"shall not (?:compete|solicit)",
                r"non-?solicit",
                r"covenant not to compete",
            ),
        ),
        RiskType(
            key="unilateral_amendment",
            name="Unilateral amendment",
            description="Counterparty can change terms alone.",
            why_it_hurts="{party} can be bound by changes it never agreed to.",
            default_redline=(
                "Require mutual written consent for any amendment; provide "
                "notice and a right to terminate on material change."
            ),
            default_severity=Severity.MEDIUM,
            patterns=(
                r"may (?:modify|amend|change) (?:these|this|the) (?:terms|agreement).{0,40}(?:at any time|sole discretion)",
                r"reserves the right to (?:modify|amend|change)",
            ),
        ),
        RiskType(
            key="warranty_disclaimer",
            name="Warranty disclaimers / 'as-is'",
            description="Removes protections you may be relying on.",
            why_it_hurts=(
                "{party} bears the risk of defects with no warranty recourse."
            ),
            default_redline=(
                "Add fitness-for-purpose and quality warranties appropriate to "
                "the deliverable."
            ),
            default_severity=Severity.MEDIUM,
            patterns=(
                r'"as is"',
                r"as-is",
                r"disclaim(?:s|er)? .{0,40}warrant",
                r"no warrant(?:y|ies) of any kind",
                r"merchantability",
            ),
        ),
        RiskType(
            key="confidentiality_asymmetry",
            name="Confidentiality asymmetry",
            description="Confidentiality obligations bind only you.",
            why_it_hurts=(
                "{party} is bound to protect information without reciprocity."
            ),
            default_redline="Mutualize confidentiality obligations.",
            default_severity=Severity.LOW,
            patterns=(
                r"receiving party (?:shall|must|agrees to) (?:keep|hold|maintain|protect)",
            ),
            mitigating_patterns=(
                r"mutual",
                r"each party",
                r"both parties",
            ),
        ),
        RiskType(
            key="payment_terms",
            name="Unbalanced payment terms",
            description=(
                "Punitive late fees, long payment windows, or unclear invoicing."
            ),
            why_it_hurts=(
                "Creates cash-flow or penalty exposure for {party}."
            ),
            default_redline=(
                "Balance payment windows, cap late fees to a reasonable rate, "
                "and define invoicing and dispute mechanics."
            ),
            default_severity=Severity.LOW,
            patterns=(
                r"late (?:fee|charge|payment).{0,20}\d+(?:\.\d+)?\s?%",
                r"interest .{0,20}\d+(?:\.\d+)?\s?% per (?:month|annum)",
                r"net\s?(?:60|90|120)",
            ),
        ),
        RiskType(
            key="assignment_restriction",
            name="Asymmetric assignment restriction",
            description="You cannot assign; they can freely.",
            why_it_hurts="Limits {party}'s flexibility while the counterparty keeps its own.",
            default_redline="Make assignment consent symmetric and not unreasonably withheld.",
            default_severity=Severity.LOW,
            patterns=(
                r"(?:may not|shall not) assign",
                r"assignment .{0,30}(?:prior written consent)",
            ),
        ),
        RiskType(
            key="force_majeure_gap",
            name="Force majeure gaps",
            description="Excuses their nonperformance but not yours.",
            why_it_hurts="{party} remains bound while the counterparty is excused.",
            default_redline="Make force majeure mutual with defined qualifying events.",
            default_severity=Severity.LOW,
            patterns=(r"force majeure",),
        ),
        RiskType(
            key="missing_sla",
            name="Missing SLA / remedies",
            description="Service obligations with no measurable standard or remedy.",
            why_it_hurts="{party} has no measurable recourse for poor performance.",
            default_redline="Add measurable SLA metrics and service credits or remedies.",
            default_severity=Severity.LOW,
            patterns=(
                r"commercially reasonable efforts",
                r"best efforts",
                r"reasonable endeavours",
            ),
        ),
        RiskType(
            key="data_protection_gap",
            name="Data protection / privacy gaps",
            description=(
                "No DPA, unclear data use, or weak security commitments."
            ),
            why_it_hurts=(
                "Leaves {party} exposed on data-handling and breach obligations."
            ),
            default_redline=(
                "Add processing terms (DPA), defined security measures, and "
                "breach-notification obligations."
            ),
            default_severity=Severity.MEDIUM,
            jurisdiction_note=(
                "Data-protection obligations (e.g. GDPR, CCPA) are mandatory in "
                "many jurisdictions and cannot be contracted away."
            ),
            patterns=(
                r"personal data",
                r"process(?:es|ing)? .{0,20}data",
                r"data protection",
            ),
            mitigating_patterns=(
                r"data processing (?:agreement|addendum)",
                r"breach notification",
            ),
        ),
        RiskType(
            key="ambiguous_terms",
            name="Ambiguous / undefined terms",
            description="Vague obligations that invite disputes.",
            why_it_hurts="Ambiguity can be resolved against {party} in a dispute.",
            default_redline="Define vague terms precisely with objective criteria.",
            default_severity=Severity.INFO,
            patterns=(
                r"as (?:reasonably )?determined by",
                r"from time to time",
                r"including but not limited to",
            ),
        ),
    ]
}


def risk(key: str) -> RiskType:
    return TAXONOMY[key]


def all_keys() -> list[str]:
    return list(TAXONOMY.keys())
