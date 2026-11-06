"""Tests for the reconciliation engine.

The closure gate is the only thing standing between a human saying "we're
done" and a recall being terminated with product still on shelves, so the
refusal paths are tested harder than the happy one.
"""

from __future__ import annotations

import pytest

from closeout.recon import (
    ConsigneeReport,
    Disposition,
    Severity,
    reconcile,
)


def report(
    name: str,
    shipped: int,
    *,
    returned: int = 0,
    destroyed: int = 0,
    quarantined: int = 0,
    dispensed: int = 0,
    attested_by: str | None = "a-person",
    claims_complete: bool = False,
) -> ConsigneeReport:
    return ConsigneeReport(
        consignee=name,
        shipped=shipped,
        disposition=Disposition(
            returned=returned,
            destroyed=destroyed,
            quarantined=quarantined,
            dispensed=dispensed,
        ),
        attested_by=attested_by,
        claims_complete=claims_complete,
    )


# --- the arithmetic -------------------------------------------------------


def test_fully_accounted_recall_may_close():
    result = reconcile("F-1170-2024", [report("Midtown Pharmacy", 500, returned=500)])

    assert result.may_close
    assert result.unaccounted == 0
    assert result.blockers() == []
    assert result.findings == []


def test_units_split_across_all_four_buckets_still_reconciles():
    result = reconcile(
        "F-1170-2024",
        [report("Harbour Foods", 1000, returned=400, destroyed=300, quarantined=200, dispensed=100)],
    )

    assert result.accounted == 1000
    assert result.unaccounted == 0
    assert result.may_close


def test_dispensed_units_count_as_accounted_but_not_recovered():
    """Product that reached a consumer is accounted for -- we know where it
    went -- yet it was never recovered. Conflating the two is how a recall
    gets reported as a success."""
    result = reconcile("F-1170-2024", [report("Corner Store", 100, dispensed=100)])

    assert result.may_close
    assert result.recovered == 0
    assert result.recovery_rate == 0.0


def test_recovery_rate_matches_the_gao_shape():
    result = reconcile(
        "F-1170-2024",
        [report("D1", 1000, returned=360, dispensed=640)],
    )

    assert result.recovery_rate == pytest.approx(0.36)


def test_recovery_rate_of_empty_recall_is_zero_not_a_crash():
    assert reconcile("F-0000-0000", []).recovery_rate == 0.0


# --- the refusals ---------------------------------------------------------


def test_unaccounted_units_block_closure():
    result = reconcile(
        "F-1170-2024",
        [report("Westside Distributors", 5000, returned=3600, dispensed=0)],
    )

    assert not result.may_close
    assert result.unaccounted == 1400
    assert any("1400 units unaccounted" in b for b in result.blockers())


def test_claiming_complete_while_short_is_a_contradiction():
    """Run B of the demo: the human asserts closure, the arithmetic refuses."""
    result = reconcile(
        "F-1170-2024",
        [
            report(
                "Westside Distributors",
                5000,
                returned=3600,
                claims_complete=True,
            )
        ],
    )

    assert not result.may_close
    codes = [f.code for f in result.findings]
    assert codes == ["false_completion"]
    assert result.contradictions
    # The contradiction is reported ahead of the bare shortfall.
    assert "reports the recall complete" in result.blockers()[0]


def test_accounting_for_more_than_was_shipped_is_a_contradiction():
    result = reconcile(
        "F-1170-2024",
        [report("Overcount Ltd", 100, returned=140)],
    )

    assert not result.may_close
    assert [f.code for f in result.findings] == ["overage"]
    assert result.reports[0].overage == 40
    # An overage must not be allowed to mask a shortfall elsewhere.
    assert result.reports[0].outstanding == 0


def test_overage_suppresses_the_weaker_finding_for_that_consignee():
    """One consignee should not produce two competing explanations."""
    result = reconcile(
        "F-1170-2024",
        [report("Overcount Ltd", 100, returned=140, claims_complete=True)],
    )

    assert [f.code for f in result.findings] == ["overage"]


def test_missing_attestation_blocks_closure_even_when_arithmetic_is_clean():
    result = reconcile(
        "F-1170-2024",
        [report("Quiet Pharmacy", 200, returned=200, attested_by=None)],
    )

    assert result.unaccounted == 0
    assert not result.may_close
    assert result.missing_attestations == ["Quiet Pharmacy"]
    assert any("no final account from" in b for b in result.blockers())


def test_duplicate_reports_for_one_consignee_are_a_contradiction():
    result = reconcile(
        "F-1170-2024",
        [
            report("Midtown Pharmacy", 500, returned=500),
            report("Midtown Pharmacy", 500, returned=500),
        ],
    )

    assert not result.may_close
    assert "duplicate_report" in [f.code for f in result.findings]


def test_a_recall_with_no_reports_cannot_be_closed():
    """An empty account is not a clean one."""
    result = reconcile("F-1170-2024", [])

    assert not result.may_close
    assert result.blockers() == [
        "no consignee reports: nothing has been accounted for"
    ]


def test_one_short_consignee_holds_the_whole_recall_open():
    result = reconcile(
        "F-1170-2024",
        [
            report("Clean A", 100, returned=100),
            report("Clean B", 100, destroyed=100),
            report("Short C", 100, returned=1),
        ],
    )

    assert not result.may_close
    assert result.unaccounted == 99
    assert any("1 consignee(s)" in b for b in result.blockers())


def test_blockers_are_ordered_contradictions_first():
    result = reconcile(
        "F-1170-2024",
        [
            report("Liar", 100, returned=10, claims_complete=True),
            report("Silent", 100, returned=100, attested_by=None),
        ],
    )

    blockers = result.blockers()
    assert "reports the recall complete" in blockers[0]
    assert "unaccounted" in blockers[1]
    assert "no final account" in blockers[2]


# --- input validation -----------------------------------------------------


def test_negative_counts_are_rejected_at_construction():
    with pytest.raises(ValueError, match="returned cannot be negative"):
        Disposition(returned=-1)


def test_negative_shipment_is_rejected():
    with pytest.raises(ValueError, match="shipped cannot be negative"):
        ConsigneeReport("X", -5, Disposition())


def test_booleans_are_not_accepted_as_counts():
    """True == 1 in Python; silently counting a flag as a unit is exactly the
    kind of quiet data fault this project exists to catch."""
    with pytest.raises(TypeError, match="returned must be an int"):
        Disposition(returned=True)


def test_reconcile_does_not_mutate_the_caller_list():
    reports = [report("A", 10, returned=10)]
    reconcile("F-1", reports)

    assert len(reports) == 1


def test_reconcile_is_deterministic():
    reports = [report("Westside", 5000, returned=3600, claims_complete=True)]
    first = reconcile("F-1", reports)
    second = reconcile("F-1", reports)

    assert first.blockers() == second.blockers()
    assert [f.code for f in first.findings] == [f.code for f in second.findings]
