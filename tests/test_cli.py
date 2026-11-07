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

    run.root = tmp_path
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


@pytest.fixture
def closed(cli):
    """A recall that reconciles and has been signed off."""
    cli("ship", "--recall", "S-1", "--consignee", "A", "--units", "1000")
    cli("file", "--recall", "S-1", "--consignee", "A",
        "--returned", "1000", "--returned-evidence", "returns-receipt/RR-1",
        "--attested-by", "D. Okafor", "--claims-complete")
    done = cli("close", "--recall", "S-1", "--authorized-by", "M. Haddad")
    assert done.returncode == 0
    return cli


def test_a_closure_is_not_overwritten(closed):
    """Closing twice would move the signature and keep the first timestamp."""
    again = closed("close", "--recall", "S-1", "--authorized-by", "the janitor")
    assert again.returncode == 2
    assert "already closed by M. Haddad" in again.stderr
    assert "the janitor" not in closed("certificate", "--recall", "S-1").stdout


def test_a_closed_recall_takes_no_further_records(closed):
    for args in (
        ("file", "--recall", "S-1", "--consignee", "A", "--returned", "1",
         "--returned-evidence", "x", "--attested-by", "y"),
        ("ship", "--recall", "S-1", "--consignee", "B", "--units", "50"),
        ("receipt", "--recall", "S-1", "--consignee", "A", "--units", "10"),
    ):
        refused = closed(*args)
        assert refused.returncode == 2, args[0]
        assert "takes no further records" in refused.stderr, args[0]


def test_the_certificate_states_the_figures_that_were_signed_for(closed):
    """The artifact must not drift from the signature it carries.

    A certificate recomputed from current state would show today's figures
    under a signature given for the figures of the day -- the assertion
    this project exists to refuse.
    """
    before = closed("certificate", "--recall", "S-1").stdout
    assert "Recovered: **1000** (100.0%)" in before

    # Even if the state file is reached around the CLI, the certificate is
    # rendered from the snapshot taken at closure, not recomputed.
    import json
    from pathlib import Path
    state_file = next(Path(closed.root).glob("S-1.json"))
    state = json.loads(state_file.read_text())
    state["accounts"]["A"]["counts"]["returned"] = 1
    state_file.write_text(json.dumps(state))

    after = closed("certificate", "--recall", "S-1").stdout
    assert after == before
    assert "Recovered: **1000** (100.0%)" in after
