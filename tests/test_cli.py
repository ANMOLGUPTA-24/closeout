"""Tests for the command line the agents actually run.

Exit codes matter here: the demo script and the agents both branch on
them, so a refusal that exits 0 would silently close a recall.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture
def cli(tmp_path):
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "closeout.cli", "--root", str(tmp_path), *args],
            cwd=REPO,
            capture_output=True,
            text=True,
        )

    return run


@pytest.fixture
def seeded(cli):
    cli("ship", "--recall", "D-1", "--consignee", "Gulf Coast", "--units", "1000")
    return cli


def test_reconcile_exits_nonzero_when_closure_is_refused(seeded):
    result = seeded("reconcile", "--recall", "D-1")

    assert result.returncode == 1
    assert "CLOSURE REFUSED" in result.stdout


def test_reconcile_exits_zero_when_it_may_close(seeded):
    seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "1000", "--returned-evidence", "rr/1",
        "--attested-by", "someone",
    )
    result = seeded("reconcile", "--recall", "D-1")

    assert result.returncode == 0
    assert "MAY CLOSE" in result.stdout


def test_close_refuses_and_exits_nonzero_while_short(seeded):
    seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "400", "--returned-evidence", "rr/1",
        "--attested-by", "someone",
    )
    result = seeded("close", "--recall", "D-1", "--authorized-by", "@regulatory")

    assert result.returncode == 1
    assert "CLOSURE REFUSED" in result.stderr


def test_filing_for_an_unknown_consignee_is_refused(seeded):
    """A typo must not silently create a consignee nobody shipped to."""
    result = seeded(
        "file", "--recall", "D-1", "--consignee", "Guulf Coast",
        "--returned", "10", "--attested-by", "someone",
    )

    assert result.returncode == 2
    assert "no shipment on record" in result.stderr


def test_file_warns_when_a_count_cites_no_document(seeded):
    result = seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "1000", "--attested-by", "someone",
    )

    assert "cites no document for: returned" in result.stdout


def test_certificate_refuses_before_closure(seeded):
    result = seeded("certificate", "--recall", "D-1")

    assert result.returncode == 1
    assert "has not been closed" in result.stderr


def test_certificate_states_what_was_never_recovered(seeded):
    seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "600", "--returned-evidence", "rr/1",
        "--dispensed", "400", "--dispensed-evidence", "pos/1",
        "--attested-by", "D. Okafor",
    )
    seeded("close", "--recall", "D-1", "--authorized-by", "M. Haddad")
    result = seeded("certificate", "--recall", "D-1")

    assert result.returncode == 0
    assert "Recovered: **600** (60.0%)" in result.stdout
    assert "Never recovered: **400**" in result.stdout
    assert "rr/1" in result.stdout
    assert "M. Haddad" in result.stdout


def test_fetch_offline_reads_the_bundled_record():
    result = subprocess.run(
        [sys.executable, "-m", "closeout.cli", "fetch",
         "--recall", "D-1572-2020", "--offline"],
        cwd=REPO, capture_output=True, text=True,
    )

    assert result.returncode == 0
    assert "9600 bottles" in result.stdout
    assert "Terminated" in result.stdout


def test_fetch_rejects_a_recall_number_it_cannot_route():
    """openFDA serves drug, food and device reports separately."""
    result = subprocess.run(
        [sys.executable, "-m", "closeout.cli", "fetch", "--recall", "QQ-1"],
        cwd=REPO, capture_output=True, text=True,
    )

    assert result.returncode == 2
    assert "D-, F- or Z-" in result.stderr


# --- the liaison must not see the cross-check ----------------------------


def test_filing_does_not_reveal_the_firms_receiving_log(seeded):
    """A liaison works in the consignee's own room. Showing it the firm's
    independent record would hand the party being checked the number its
    paperwork has to agree with, which is the one check that does not rest
    on the consignee's own self-consistency."""
    seeded("receipt", "--recall", "D-1", "--consignee", "Gulf Coast", "--units", "600")
    result = seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "1000", "--returned-evidence", "rr/1",
        "--attested-by", "D. Okafor",
    )

    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "600" not in combined
    assert "receiving log" not in combined.lower()
    assert "disputed" not in combined.lower()


def test_the_registrar_does_see_the_dispute(seeded):
    """Same data, the other room."""
    seeded("receipt", "--recall", "D-1", "--consignee", "Gulf Coast", "--units", "600")
    seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "1000", "--returned-evidence", "rr/1",
        "--attested-by", "D. Okafor",
    )
    result = seeded("reconcile", "--recall", "D-1")

    assert result.returncode == 1
    assert "firm logged 600" in result.stdout
    assert "400 units are claimed as returned" in result.stdout


def test_filing_a_short_account_still_succeeds(seeded):
    """Filing records what someone said; it does not pass judgement. The
    verdict is the registrar's, so a short filing must not exit non-zero."""
    result = seeded(
        "file", "--recall", "D-1", "--consignee", "Gulf Coast",
        "--returned", "400", "--returned-evidence", "rr/1",
        "--attested-by", "D. Okafor",
    )

    assert result.returncode == 0
    assert "unaccounted 600" in result.stdout
    assert seeded("reconcile", "--recall", "D-1").returncode == 1


def test_negative_units_rejected_before_anything_is_written(cli):
    """A negative count must not reach the state file.

    The dataclasses reject negatives, but only when a record is read back.
    If the CLI persists one first, every later reconcile, close and
    certificate raises and the recall is unusable until someone refiles by
    hand -- a fat-finger mid-demo would brick it.
    """
    assert cli("ship", "--recall", "N-1", "--consignee", "A", "--units", "-500").returncode == 2

    # Nothing was written, so a later read still works.
    assert cli("ship", "--recall", "N-1", "--consignee", "A", "--units", "100").returncode == 0
    done = cli("reconcile", "--recall", "N-1")
    assert done.returncode != 0          # still unaccounted for, correctly refused
    assert "shipped       100" in done.stdout


def test_negative_bucket_rejected_and_account_not_filed(cli):
    cli("ship", "--recall", "N-2", "--consignee", "A", "--units", "100")
    bad = cli("file", "--recall", "N-2", "--consignee", "A",
              "--returned", "-10", "--attested-by", "X")
    assert bad.returncode == 2
    assert "cannot be negative" in bad.stderr

    # The account was not half-written: reconcile still reads, and reports
    # no account filed rather than tracebacking.
    after = cli("reconcile", "--recall", "N-2")
    assert "Traceback" not in after.stderr
    assert "no account filed" in after.stdout


def test_non_numeric_units_rejected(cli):
    bad = cli("ship", "--recall", "N-3", "--consignee", "A", "--units", "abc")
    assert bad.returncode == 2
    assert "not a whole number of units" in bad.stderr
