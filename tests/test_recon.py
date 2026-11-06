"""Tests for the reconciliation engine.

The closure gate is the only thing between a human saying "we're done" and
a recall being terminated with product still on shelves, so the refusal
paths are tested harder than the happy one.
"""

from __future__ import annotations

import pytest

from closeout.recon import (
    ConsigneeReport,
    Count,
    Disposition,
    Severity,
    reconcile,
)

RECEIPT = "returns-receipt/RR-4471"
CERT = "destruction-cert/DC-118"
POS = "pos-export/2018-03-14"
LOG = "quarantine-log/Q-22"


def report(
    name: str,
    shipped: int,
    *,
    returned: int = 0,
    destroyed: int = 0,
    quarantined: int = 0,
    dispensed: int = 0,
    evidenced: bool = True,
    attested_by: str | None = "a-person",
    claims_complete: bool = False,
    independent_returns: int | None = None,
) -> ConsigneeReport:
    """A report whose counts all cite evidence unless told otherwise."""

    def count(units: int, reference: str) -> Count:
        return Count(units, reference if (units and evidenced) else None)

    return ConsigneeReport(
        consignee=name,
        shipped=shipped,
        disposition=Disposition(
            returned=count(returned, RECEIPT),
            destroyed=count(destroyed, CERT),
            quarantined=count(quarantined, LOG),
            dispensed=count(dispensed, POS),
        ),
        attested_by=attested_by,
        claims_complete=claims_complete,
        independent_returns=independent_returns,
    )


# --- the arithmetic -------------------------------------------------------


def test_fully_accounted_and_evidenced_recall_may_close():
    result = reconcile("F-0616-2018", [report("Midtown Pharmacy", 500, returned=500)])

    assert result.may_close
    assert result.unaccounted == 0
    assert result.blockers() == []
    assert result.findings == []


def test_units_split_across_all_four_buckets_still_reconciles():
    result = reconcile(
        "F-0616-2018",
        [report("Harbour Foods", 1000, returned=400, destroyed=300, quarantined=200, dispensed=100)],
    )

    assert result.accounted == 1000
    assert result.may_close


def test_dispensed_units_count_as_accounted_but_not_recovered():
    """Product that reached a consumer is accounted for -- we know where it
    went -- yet it was never recovered. Conflating the two is how a recall
    gets reported as a success."""
    result = reconcile("F-0616-2018", [report("Corner Store", 100, dispensed=100)])

    assert result.may_close
    assert result.recovered == 0
    assert result.recovery_rate == 0.0


def test_recovery_rate_matches_the_gao_shape():
    result = reconcile("F-0616-2018", [report("D1", 1000, returned=360, dispensed=640)])

    assert result.recovery_rate == pytest.approx(0.36)


def test_recovery_rate_of_empty_recall_is_zero_not_a_crash():
    assert reconcile("F-0000-0000", []).recovery_rate == 0.0


# --- unaccounted ----------------------------------------------------------


def test_unaccounted_units_block_closure():
    result = reconcile(
        "F-0616-2018",
        [report("Westside Distributors", 5000, returned=3600)],
    )

    assert not result.may_close
    assert result.unaccounted == 1400
    assert [f.code for f in result.findings] == ["unaccounted"]


def test_claiming_complete_while_short_is_a_contradiction():
    """Run B of the demo: the human asserts closure, the arithmetic refuses."""
    result = reconcile(
        "F-0616-2018",
        [report("Westside Distributors", 5000, returned=3600, claims_complete=True)],
    )

    assert not result.may_close
    assert [f.code for f in result.findings] == ["false_completion"]
    assert "reports the recall complete" in result.blockers()[0]


def test_accounting_for_more_than_was_shipped_is_a_contradiction():
    result = reconcile("F-0616-2018", [report("Overcount Ltd", 100, returned=140)])

    assert not result.may_close
    assert [f.code for f in result.findings] == ["overage"]
    assert result.reports[0].overage == 40


def test_overage_suppresses_every_weaker_finding_for_that_consignee():
    """One consignee should not produce competing explanations: if the
    counts exceed the shipment, the counts are what is wrong."""
    result = reconcile(
        "F-0616-2018",
        [
            report(
                "Overcount Ltd",
                100,
                returned=140,
                evidenced=False,
                claims_complete=True,
                independent_returns=10,
            )
        ],
    )

    assert [f.code for f in result.findings] == ["overage"]


def test_one_short_consignee_holds_the_whole_recall_open():
    result = reconcile(
        "F-0616-2018",
        [
            report("Clean A", 100, returned=100),
            report("Clean B", 100, destroyed=100),
            report("Short C", 100, returned=1),
        ],
    )

    assert not result.may_close
    assert result.unaccounted == 99


# --- evidence -------------------------------------------------------------


def test_a_count_citing_no_document_blocks_closure():
    """The numbers add up perfectly. That is not enough."""
    result = reconcile(
        "F-0616-2018",
        [report("Westside Distributors", 500, returned=500, evidenced=False)],
    )

    assert result.unaccounted == 0
    assert not result.may_close
    assert [f.code for f in result.findings] == ["unevidenced_returned"]
    assert "citing no document" in result.blockers()[0]


def test_unevidenced_recovery_is_called_out_as_recovery():
    result = reconcile(
        "F-0616-2018",
        [report("Westside", 100, destroyed=100, evidenced=False)],
    )

    assert "counted as recovered" in result.findings[0].detail


def test_unevidenced_non_recovery_bucket_is_not_called_recovery():
    result = reconcile(
        "F-0616-2018",
        [report("Westside", 100, dispensed=100, evidenced=False)],
    )

    assert [f.code for f in result.findings] == ["unevidenced_dispensed"]
    assert "counted as recovered" not in result.findings[0].detail


def test_zero_counts_need_no_evidence():
    """Nobody has to produce a receipt for having destroyed nothing."""
    result = reconcile("F-0616-2018", [report("Midtown", 100, returned=100)])

    assert result.findings == []


def test_blank_evidence_is_not_evidence():
    result = reconcile(
        "F-0616-2018",
        [
            ConsigneeReport(
                "Westside",
                100,
                Disposition(returned=Count(100, "   ")),
                attested_by="someone",
            )
        ],
    )

    assert [f.code for f in result.findings] == ["unevidenced_returned"]


def test_evidenced_recovery_rate_excludes_uncited_counts():
    result = reconcile(
        "F-0616-2018",
        [
            ConsigneeReport(
                "Westside",
                1000,
                Disposition(
                    returned=Count(600, RECEIPT),
                    destroyed=Count(400),
                ),
                attested_by="someone",
            )
        ],
    )

    assert result.recovered == 1000
    assert result.evidenced_recovered == 600
    assert result.evidenced_recovery_rate == pytest.approx(0.6)


# --- cross-source adjudication -------------------------------------------


def test_claimed_returns_above_the_firms_receiving_log_is_a_contradiction():
    """The consignee says it sent 2,878 back. The firm logged 2,600
    arriving. Both numbers are internally consistent; they cannot both be
    true."""
    result = reconcile(
        "F-0616-2018",
        [
            report(
                "Westside Distributors",
                4278,
                returned=2878,
                destroyed=900,
                quarantined=300,
                dispensed=200,
                independent_returns=2600,
            )
        ],
    )

    assert not result.may_close
    assert [f.code for f in result.findings] == ["returns_disputed"]
    assert "278 units are claimed as returned and were never received" in (
        result.findings[0].detail
    )


def test_more_received_than_claimed_is_also_a_contradiction():
    result = reconcile(
        "F-0616-2018",
        [report("Westside", 1000, returned=600, dispensed=400, independent_returns=700)],
    )

    assert [f.code for f in result.findings] == ["returns_disputed"]
    assert "100 more came back" in result.findings[0].detail


def test_agreeing_records_raise_nothing():
    result = reconcile(
        "F-0616-2018",
        [report("Westside", 1000, returned=1000, independent_returns=1000)],
    )

    assert result.findings == []
    assert result.may_close


def test_no_independent_record_means_no_dispute_can_be_detected():
    """Absence of a receiving log is not agreement. It just means this
    particular check cannot run."""
    result = reconcile("F-0616-2018", [report("Westside", 1000, returned=1000)])

    assert result.reports[0].returns_gap is None
    assert result.may_close


# --- attestation ----------------------------------------------------------


def test_missing_attestation_blocks_closure_even_when_everything_adds_up():
    result = reconcile(
        "F-0616-2018",
        [report("Quiet Pharmacy", 200, returned=200, attested_by=None)],
    )

    assert result.unaccounted == 0
    assert not result.may_close
    assert result.missing_attestations == ["Quiet Pharmacy"]


def test_duplicate_reports_for_one_consignee_are_a_contradiction():
    result = reconcile(
        "F-0616-2018",
        [
            report("Midtown Pharmacy", 500, returned=500),
            report("Midtown Pharmacy", 500, returned=500),
        ],
    )

    assert not result.may_close
    assert "duplicate_report" in [f.code for f in result.findings]


def test_a_recall_with_no_reports_cannot_be_closed():
    """An empty account is not a clean one."""
    result = reconcile("F-0616-2018", [])

    assert not result.may_close
    assert result.blockers() == ["no consignee reports: nothing has been accounted for"]


def test_blockers_are_ordered_worst_first():
    result = reconcile(
        "F-0616-2018",
        [
            report("Liar", 100, returned=10, claims_complete=True),
            report("Vague", 100, returned=100, evidenced=False),
            report("Short", 100, returned=10),
            report("Silent", 100, returned=100, attested_by=None),
        ],
    )

    blockers = result.blockers()
    assert "reports the recall complete" in blockers[0]
    assert "citing no document" in blockers[1]
    assert "unaccounted for and presumed" in blockers[2]
    assert "no final account" in blockers[3]


# --- input validation -----------------------------------------------------


def test_negative_counts_are_rejected_at_construction():
    with pytest.raises(ValueError, match="units cannot be negative"):
        Count(-1)


def test_negative_shipment_is_rejected():
    with pytest.raises(ValueError, match="shipped cannot be negative"):
        ConsigneeReport("X", -5, Disposition())


def test_negative_independent_returns_is_rejected():
    with pytest.raises(ValueError, match="independent_returns cannot be negative"):
        ConsigneeReport("X", 5, Disposition(), independent_returns=-1)


def test_booleans_are_not_accepted_as_counts():
    """True == 1 in Python; silently counting a flag as a unit is exactly
    the kind of quiet data fault this project exists to catch."""
    with pytest.raises(TypeError, match="units must be an int"):
        Count(True)


def test_reconcile_does_not_mutate_the_caller_list():
    reports = [report("A", 10, returned=10)]
    reconcile("F-1", reports)

    assert len(reports) == 1


def test_reconcile_is_deterministic():
    reports = [report("Westside", 5000, returned=3600, claims_complete=True)]
    first = reconcile("F-1", reports)
    second = reconcile("F-1", reports)

    assert first.blockers() == second.blockers()
