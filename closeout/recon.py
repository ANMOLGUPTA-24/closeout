"""Deterministic recall reconciliation.

The whole point of Closeout: a recall is closed by arithmetic and evidence,
never by assertion. Nothing in this module calls a model or estimates a
number. The agent in the room reads these results and reports them; it does
not compute them, and it cannot talk its way past them.

Three things can be wrong with a consignee's account, and they are not the
same thing:

  *unaccounted*  the numbers do not add up to what was shipped. Product is
                 in the market and nobody can point to it.
  *unevidenced*  the numbers add up, but a count rests on nothing. "We
                 returned 2,878" with no receipt is a sentence, not a fact.
  *disputed*     the consignee's number and an independent record disagree.
                 Someone is wrong, and reconciliation cannot say who.

Self-consistency is the weakest of the three. A consignee that wants to
close a recall early can produce internally consistent numbers all day.

Vocabulary, matching how a recall is actually accounted for:

  shipped      units a consignee received of the recalled lot
  returned     units sent back to the firm
  destroyed    units destroyed on site
  quarantined  units held, off-sale, not yet returned or destroyed
  dispensed    units that reached an end consumer and cannot be recovered
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "Count",
    "Disposition",
    "ConsigneeReport",
    "Finding",
    "Severity",
    "ReconResult",
    "reconcile",
    "BUCKETS",
]

#: The four places a shipped unit can end up. Order is reporting order.
BUCKETS = ("returned", "destroyed", "quarantined", "dispensed")

#: Buckets whose claim is that product is physically back under control.
#: These are what the recovery rate is made of, so an unevidenced one is
#: the most consequential kind of unevidenced claim.
RECOVERY_BUCKETS = ("returned", "destroyed")


class Severity(str, Enum):
    """How badly a consignee's account fails to hold up.

    Every severity but ``OK`` blocks closure. They differ in what a person
    has to go and do about it.
    """

    OK = "ok"
    #: Internally consistent, but product is still in the market.
    OPEN = "open"
    #: A count rests on no document.
    UNEVIDENCED = "unevidenced"
    #: The account contradicts itself, the shipment record, or another source.
    CONTRADICTION = "contradiction"


@dataclass(frozen=True)
class Count:
    """A number of units, and the document it rests on.

    ``evidence`` is a reference a person could go and pull: a returns
    receipt number, a destruction certificate, a POS export id. ``None``
    means the consignee asserted the figure and cited nothing.
    """

    units: int
    evidence: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.units, int) or isinstance(self.units, bool):
            raise TypeError(f"units must be an int, got {self.units!r}")
        if self.units < 0:
            raise ValueError(f"units cannot be negative, got {self.units}")

    @property
    def evidenced(self) -> bool:
        return bool(self.evidence and self.evidence.strip())


@dataclass(frozen=True)
class Disposition:
    """Where a consignee says its units went. Counts, not claims."""

    returned: Count = Count(0)
    destroyed: Count = Count(0)
    quarantined: Count = Count(0)
    dispensed: Count = Count(0)

    @property
    def accounted(self) -> int:
        return sum(getattr(self, bucket).units for bucket in BUCKETS)

    def unevidenced(self) -> list[tuple[str, int]]:
        """Non-zero counts citing no document, in reporting order."""
        out = []
        for bucket in BUCKETS:
            count = getattr(self, bucket)
            if count.units and not count.evidenced:
                out.append((bucket, count.units))
        return out


@dataclass(frozen=True)
class ConsigneeReport:
    """One consignee's account of one recalled lot.

    ``attested_by`` is the human act: a named person said "this is my final
    account". ``claims_complete`` is their assertion that nothing is
    outstanding, which reconciliation may well contradict.

    ``independent_returns`` is the firm's own receiving log: how many units
    it recorded actually arriving back from this consignee. It comes from
    the other side of the transaction, so where it disagrees with the
    consignee's figure, neither one can be taken on trust.
    """

    consignee: str
    shipped: int
    disposition: Disposition
    attested_by: str | None = None
    claims_complete: bool = False
    independent_returns: int | None = None

    def __post_init__(self) -> None:
        if self.shipped < 0:
            raise ValueError(f"shipped cannot be negative, got {self.shipped}")
        if self.independent_returns is not None and self.independent_returns < 0:
            raise ValueError("independent_returns cannot be negative")

    @property
    def attested(self) -> bool:
        return bool(self.attested_by)

    @property
    def unaccounted(self) -> int:
        """Shipped minus accounted. Negative means more than exists."""
        return self.shipped - self.disposition.accounted

    @property
    def overage(self) -> int:
        return max(0, -self.unaccounted)

    @property
    def outstanding(self) -> int:
        """Unaccounted units, floored at zero for summing."""
        return max(0, self.unaccounted)

    @property
    def returns_gap(self) -> int | None:
        """Consignee's claimed returns minus the firm's receiving log.

        None when there is no independent record to compare against, which
        is itself worth knowing: the figure is uncorroborated.
        """
        if self.independent_returns is None:
            return None
        return self.disposition.returned.units - self.independent_returns


@dataclass(frozen=True)
class Finding:
    """One reason, in plain words, that this consignee is not settled."""

    consignee: str
    severity: Severity
    code: str
    detail: str


@dataclass
class ReconResult:
    """The arithmetic, and the single closure decision that follows."""

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
            sum(getattr(r.disposition, b).units for b in RECOVERY_BUCKETS)
            for r in self.reports
        )

    @property
    def evidenced_recovered(self) -> int:
        """Recovered units whose count cites a document.

        The honest recovery figure. Everything else is somebody's word.
        """
        total = 0
        for report in self.reports:
            for bucket in RECOVERY_BUCKETS:
                count = getattr(report.disposition, bucket)
                if count.evidenced:
                    total += count.units
        return total

    @property
    def recovery_rate(self) -> float:
        return self.recovered / self.shipped if self.shipped else 0.0

    @property
    def evidenced_recovery_rate(self) -> float:
        return self.evidenced_recovered / self.shipped if self.shipped else 0.0

    @property
    def missing_attestations(self) -> list[str]:
        return [r.consignee for r in self.reports if not r.attested]

    def by_severity(self, severity: Severity) -> list[Finding]:
        return [f for f in self.findings if f.severity is severity]

    @property
    def contradictions(self) -> list[Finding]:
        return self.by_severity(Severity.CONTRADICTION)

    @property
    def may_close(self) -> bool:
        """True only when nothing is outstanding against any consignee.

        Every finding blocks. A recall with an unevidenced count closes no
        more readily than one that is short.
        """
        return (
            bool(self.reports)
            and not self.findings
            and not self.missing_attestations
        )

    def blockers(self) -> list[str]:
        """Why closure is refused, worst first. Empty iff may_close."""
        if not self.reports:
            return ["no consignee reports: nothing has been accounted for"]

        out: list[str] = []
        for severity in (
            Severity.CONTRADICTION,
            Severity.UNEVIDENCED,
            Severity.OPEN,
        ):
            out += [f"{f.consignee}: {f.detail}" for f in self.by_severity(severity)]
        if self.missing_attestations:
            out.append(
                "no final account from " + ", ".join(sorted(self.missing_attestations))
            )
        return out


def _check_overage(report: ConsigneeReport) -> Finding | None:
    if not report.overage:
        return None
    return Finding(
        report.consignee,
        Severity.CONTRADICTION,
        "overage",
        f"accounts for {report.disposition.accounted} units but was shipped "
        f"{report.shipped}: {report.overage} more than exist, so the shipment "
        "record or the count is wrong",
    )


def _check_returns_dispute(report: ConsigneeReport) -> Finding | None:
    gap = report.returns_gap
    if not gap:
        return None
    claimed = report.disposition.returned.units
    logged = report.independent_returns
    if gap > 0:
        detail = (
            f"claims {claimed} units returned, but the firm's receiving log "
            f"records {logged} arriving back: {gap} units are claimed as "
            "returned and were never received"
        )
    else:
        detail = (
            f"claims {claimed} units returned, but the firm's receiving log "
            f"records {logged} arriving back: {-gap} more came back than the "
            "consignee accounts for, so one of the two records is wrong"
        )
    return Finding(report.consignee, Severity.CONTRADICTION, "returns_disputed", detail)


def _check_false_completion(report: ConsigneeReport) -> Finding | None:
    if not (report.claims_complete and report.outstanding):
        return None
    return Finding(
        report.consignee,
        Severity.CONTRADICTION,
        "false_completion",
        f"reports the recall complete while {report.outstanding} of "
        f"{report.shipped} units are still unaccounted for",
    )


def _check_unevidenced(report: ConsigneeReport) -> list[Finding]:
    out = []
    for bucket, units in report.disposition.unevidenced():
        weight = (
            " and it is counted as recovered"
            if bucket in RECOVERY_BUCKETS
            else ""
        )
        out.append(
            Finding(
                report.consignee,
                Severity.UNEVIDENCED,
                f"unevidenced_{bucket}",
                f"claims {units} units {bucket} citing no document{weight}",
            )
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

        # An overage means the counts themselves cannot be trusted, so
        # nothing further is worth saying about this consignee's buckets.
        overage = _check_overage(report)
        if overage:
            result.findings.append(overage)
            continue

        for check in (_check_returns_dispute, _check_false_completion):
            finding = check(report)
            if finding:
                result.findings.append(finding)

        result.findings += _check_unevidenced(report)

        # Only report a bare shortfall when nothing sharper already says so.
        if report.outstanding and not report.claims_complete:
            result.findings.append(
                Finding(
                    report.consignee,
                    Severity.OPEN,
                    "unaccounted",
                    f"{report.outstanding} of {report.shipped} units "
                    "unaccounted for and presumed still in the market",
                )
            )

    return result
