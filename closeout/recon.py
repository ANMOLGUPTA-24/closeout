"""Deterministic recall reconciliation.

The whole point of Closeout: a recall is closed by arithmetic, never by
assertion. Nothing in this module calls a model or estimates a number. The
agent in the room reads these results and reports them; it does not compute
them, and it cannot talk its way past them.

Vocabulary, matching how a recall is actually accounted for:

  shipped      units a consignee received of the recalled lot
  returned     units sent back to the firm
  destroyed    units destroyed on site with evidence
  quarantined  units held, off-sale, not yet returned or destroyed
  dispensed    units that reached an end consumer and cannot be recovered

A unit is *accounted for* when it sits in one of those four buckets. The
residue is unaccounted: product that is somewhere in the market and that
nobody can point to. That residue is what keeps a recall open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Disposition",
    "ConsigneeReport",
    "Finding",
    "Severity",
    "ReconResult",
    "reconcile",
]


class Severity(str, Enum):
    """How badly a single consignee's report fails to hold up."""

    OK = "ok"
    #: Numbers are internally consistent but product is still in the market.
    OPEN = "open"
    #: The report contradicts itself or the shipment record.
    CONTRADICTION = "contradiction"


@dataclass(frozen=True)
class Disposition:
    """Where a consignee says its units went. Counts, not claims."""

    returned: int = 0
    destroyed: int = 0
    quarantined: int = 0
    dispensed: int = 0

    def __post_init__(self) -> None:
        for name in ("returned", "destroyed", "quarantined", "dispensed"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an int, got {value!r}")
            if value < 0:
                raise ValueError(f"{name} cannot be negative, got {value}")

    @property
    def accounted(self) -> int:
        return self.returned + self.destroyed + self.quarantined + self.dispensed


@dataclass(frozen=True)
class ConsigneeReport:
    """One consignee's account of one recalled lot.

    ``attested`` is the human act: a named person in that consignee's room
    said "this is my final account". ``claims_complete`` is their assertion
    that nothing is outstanding -- which reconciliation may well contradict.
    """

    consignee: str
    shipped: int
    disposition: Disposition
    attested_by: str | None = None
    claims_complete: bool = False

    def __post_init__(self) -> None:
        if self.shipped < 0:
            raise ValueError(f"shipped cannot be negative, got {self.shipped}")

    @property
    def attested(self) -> bool:
        return bool(self.attested_by)

    @property
    def unaccounted(self) -> int:
        """Units neither returned, destroyed, held, nor known-dispensed.

        Negative when a consignee accounts for more than it was shipped,
        which is a data fault, not a surplus. Callers read ``overage``.
        """
        return self.shipped - self.disposition.accounted

    @property
    def overage(self) -> int:
        return max(0, -self.unaccounted)

    @property
    def outstanding(self) -> int:
        """Unaccounted units, floored at zero for summing."""
        return max(0, self.unaccounted)


@dataclass(frozen=True)
class Finding:
    """One reason, in plain words, that this consignee is not settled."""

    consignee: str
    severity: Severity
    code: str
    detail: str


@dataclass
class ReconResult:
    """The arithmetic, and the single closure decision that follows from it."""

    recall_number: str
    reports: list[ConsigneeReport]
    findings: list[Finding] = field(default_factory=list)

    @property
    def shipped(self) -> int:
        return sum(r.shipped for r in self.reports)

    @property
    def accounted(self) -> int:
        return sum(r.disposition.accounted for r in self.reports)

    @property
    def unaccounted(self) -> int:
        return sum(r.outstanding for r in self.reports)

    @property
    def recovered(self) -> int:
        """Units physically back under control: returned or destroyed."""
        return sum(
            r.disposition.returned + r.disposition.destroyed for r in self.reports
        )

    @property
    def recovery_rate(self) -> float:
        """Share of shipped units recovered, 0.0 when nothing shipped.

        This is the number GAO put at about 36% for food recalls.
        """
        return self.recovered / self.shipped if self.shipped else 0.0

    @property
    def missing_attestations(self) -> list[str]:
        return [r.consignee for r in self.reports if not r.attested]

    @property
    def contradictions(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.CONTRADICTION]

    @property
    def may_close(self) -> bool:
        """True only when every unit is accounted for and every consignee has
        attested, with no contradiction outstanding."""
        return (
            bool(self.reports)
            and self.unaccounted == 0
            and not self.missing_attestations
            and not self.contradictions
        )

    def blockers(self) -> list[str]:
        """Why closure is refused, ordered worst first. Empty iff may_close."""
        if not self.reports:
            return ["no consignee reports: nothing has been accounted for"]
        out = [f"{f.consignee}: {f.detail}" for f in self.contradictions]
        if self.unaccounted:
            out.append(
                f"{self.unaccounted} units unaccounted for across "
                f"{sum(1 for r in self.reports if r.outstanding)} consignee(s)"
            )
        if self.missing_attestations:
            out.append(
                "no final account from " + ", ".join(sorted(self.missing_attestations))
            )
        return out


def reconcile(recall_number: str, reports: list[ConsigneeReport]) -> ReconResult:
    """Reconcile every consignee report for one recall.

    Pure: same inputs, same findings, every time.
    """
    result = ReconResult(recall_number=recall_number, reports=list(reports))

    seen: set[str] = set()
    for report in reports:
        if report.consignee in seen:
            result.findings.append(
                Finding(
                    report.consignee,
                    Severity.CONTRADICTION,
                    "duplicate_report",
                    "two separate accounts filed for the same consignee; "
                    "one of them is wrong",
                )
            )
        seen.add(report.consignee)

        if report.overage:
            result.findings.append(
                Finding(
                    report.consignee,
                    Severity.CONTRADICTION,
                    "overage",
                    f"accounts for {report.disposition.accounted} units but was "
                    f"shipped {report.shipped}: {report.overage} more than exist, "
                    "so the shipment record or the count is wrong",
                )
            )
            continue

        if report.claims_complete and report.outstanding:
            result.findings.append(
                Finding(
                    report.consignee,
                    Severity.CONTRADICTION,
                    "false_completion",
                    f"reports the recall complete while {report.outstanding} of "
                    f"{report.shipped} units are still unaccounted for",
                )
            )
        elif report.outstanding:
            result.findings.append(
                Finding(
                    report.consignee,
                    Severity.OPEN,
                    "unaccounted",
                    f"{report.outstanding} of {report.shipped} units unaccounted "
                    "for and presumed still in the market",
                )
            )

    return result
