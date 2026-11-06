"""Tests for the on-disk recall state.

A recall outlives the code that first wrote its file, so reading an older
file is a real case, not a hypothetical one.
"""

from __future__ import annotations

import json

import pytest

from closeout.recon import reconcile
from closeout.store import RecallStore


@pytest.fixture
def store(tmp_path):
    return RecallStore("F-0616-2018", root=tmp_path)


def test_a_file_written_before_a_key_existed_still_loads(store):
    """The receiving log was added after the first recalls were recorded.
    An older file must degrade to "nothing recorded", not raise."""
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(
        json.dumps(
            {
                "recall_number": "F-0616-2018",
                "shipments": {"Westside": 100},
                "accounts": {},
            }
        )
    )

    state = store.load()
    assert state["receiving_log"] == {}
    assert state["shipments"] == {"Westside": 100}

    store.record_receipt("Westside", 80)
    assert store.load()["receiving_log"] == {"Westside": 80}


def test_refiling_keeps_the_superseded_account(store):
    """That a consignee changed its number is itself evidence."""
    store.set_shipment("Westside", 100)
    store.file_account(
        "Westside",
        counts={"returned": 40},
        evidence={"returned": "rr/1"},
        attested_by="someone",
    )
    store.file_account(
        "Westside",
        counts={"returned": 90},
        evidence={"returned": "rr/1"},
        attested_by="someone",
    )

    state = store.load()
    assert len(state["history"]) == 1
    assert state["history"][0]["counts"]["returned"] == 40
    assert state["accounts"]["Westside"]["counts"]["returned"] == 90


def test_a_consignee_that_never_files_still_appears(store):
    """Silence must not read as completion."""
    store.set_shipment("Quiet Pharmacy", 500)

    reports = store.reports()
    assert len(reports) == 1
    assert reports[0].shipped == 500
    assert not reports[0].attested
    assert not reconcile("F-0616-2018", reports).may_close


def test_the_receiving_log_survives_a_consignee_refiling(store):
    """The firm's record is the other side of the transaction: a consignee
    must not be able to overwrite it by filing again."""
    store.set_shipment("Westside", 100)
    store.record_receipt("Westside", 60)
    store.file_account(
        "Westside",
        counts={"returned": 100},
        evidence={"returned": "rr/1"},
        attested_by="someone",
    )

    assert store.load()["receiving_log"]["Westside"] == 60
    assert store.reports()[0].independent_returns == 60
    assert store.reports()[0].returns_gap == 40


def test_evidence_round_trips_through_disk(store):
    store.set_shipment("Westside", 100)
    store.file_account(
        "Westside",
        counts={"returned": 60, "destroyed": 40},
        evidence={"returned": "rr/1", "destroyed": None},
        attested_by="someone",
    )

    disposition = store.reports()[0].disposition
    assert disposition.returned.evidenced
    assert not disposition.destroyed.evidenced
    assert disposition.unevidenced() == [("destroyed", 40)]


def test_a_recall_number_cannot_escape_the_state_directory(store, tmp_path):
    """Recall numbers arrive from an outside database."""
    hostile = RecallStore("../../etc/passwd", root=tmp_path)

    assert hostile.path.parent == tmp_path
    assert "/" not in hostile.path.name
