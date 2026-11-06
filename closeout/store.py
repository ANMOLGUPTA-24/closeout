"""Filed accounts, on disk.

A filed account is a record that a named person at a consignee stated their
final counts. It is append-only in spirit: refiling replaces a consignee's
account and keeps the previous one in ``history``, because "they changed
their number" is itself something a regulator wants to see.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from closeout.recon import BUCKETS, ConsigneeReport, Count, Disposition

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "data" / "recalls"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RecallStore:
    """One JSON file per recall."""

    def __init__(self, recall_number: str, root: Path | None = None) -> None:
        self.recall_number = recall_number
        self.root = Path(root) if root else DEFAULT_ROOT
        # Recall numbers contain dots and slashes in the wild; keep the
        # filename flat so a crafted number cannot escape the directory.
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in recall_number)
        self.path = self.root / f"{safe}.json"

    # --- persistence ------------------------------------------------------

    def _empty(self) -> dict[str, Any]:
        return {
            "recall_number": self.recall_number,
            "product": "",
            "shipments": {},
            "accounts": {},
            "receiving_log": {},
            "history": [],
            "closure": None,
        }

    def load(self) -> dict[str, Any]:
        """Read the recall's state, filling in any key the file predates.

        A file written before a key existed is missing it, and a recall
        outlives the code that first wrote it. Backfilling here means an
        older file degrades to "nothing recorded yet" for that key rather
        than raising halfway through a reconciliation.
        """
        state = self._empty()
        if not self.path.exists():
            return state
        with self.path.open() as fh:
            state.update(json.load(fh))
        return state

    def save(self, state: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
            fh.write("\n")
        tmp.replace(self.path)

    # --- mutation ---------------------------------------------------------

    def set_shipment(self, consignee: str, shipped: int, product: str = "") -> None:
        state = self.load()
        state["shipments"][consignee] = int(shipped)
        if product:
            state["product"] = product
        self.save(state)

    def file_account(
        self,
        consignee: str,
        *,
        counts: dict[str, int],
        evidence: dict[str, str | None],
        attested_by: str | None = None,
        claims_complete: bool = False,
    ) -> None:
        state = self.load()
        if consignee in state["accounts"]:
            state["history"].append(
                {"superseded_at": _now(), **state["accounts"][consignee]}
            )
        state["accounts"][consignee] = {
            "consignee": consignee,
            "counts": {b: int(counts.get(b, 0)) for b in BUCKETS},
            "evidence": {b: (evidence.get(b) or None) for b in BUCKETS},
            "attested_by": attested_by,
            "claims_complete": bool(claims_complete),
            "filed_at": _now(),
        }
        self.save(state)

    def record_receipt(self, consignee: str, units: int) -> None:
        """Record what the firm's own receiving log says came back.

        This is the other side of the transaction, so it is kept apart from
        anything the consignee filed and is never overwritten by it.
        """
        state = self.load()
        state["receiving_log"][consignee] = int(units)
        self.save(state)

    def record_closure(self, authorized_by: str, recovery_rate: float) -> None:
        state = self.load()
        state["closure"] = {
            "authorized_by": authorized_by,
            "recovery_rate": round(recovery_rate, 4),
            "closed_at": _now(),
        }
        self.save(state)

    # --- reading ----------------------------------------------------------

    def reports(self) -> list[ConsigneeReport]:
        """Every consignee with a shipment, whether or not it has filed.

        A consignee that received product and has said nothing is a report
        with no attestation, which is what holds the recall open. Dropping it
        would let silence read as completion.
        """
        state = self.load()
        receiving_log = state.get("receiving_log", {})
        out: list[ConsigneeReport] = []
        for consignee, shipped in sorted(state["shipments"].items()):
            account = state["accounts"].get(consignee, {})
            counts = account.get("counts", {})
            evidence = account.get("evidence", {})
            out.append(
                ConsigneeReport(
                    consignee=consignee,
                    shipped=int(shipped),
                    disposition=Disposition(
                        **{
                            bucket: Count(
                                int(counts.get(bucket, 0)),
                                evidence.get(bucket),
                            )
                            for bucket in BUCKETS
                        }
                    ),
                    attested_by=account.get("attested_by") or None,
                    claims_complete=bool(account.get("claims_complete", False)),
                    independent_returns=(
                        int(receiving_log[consignee])
                        if consignee in receiving_log
                        else None
                    ),
                )
            )
        return out
