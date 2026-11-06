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

from closeout.recon import ConsigneeReport, Disposition

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

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "recall_number": self.recall_number,
                "product": "",
                "shipments": {},
                "accounts": {},
                "history": [],
                "closure": None,
            }
        with self.path.open() as fh:
            return json.load(fh)

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
        returned: int = 0,
        destroyed: int = 0,
        quarantined: int = 0,
        dispensed: int = 0,
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
            "returned": int(returned),
            "destroyed": int(destroyed),
            "quarantined": int(quarantined),
            "dispensed": int(dispensed),
            "attested_by": attested_by,
            "claims_complete": bool(claims_complete),
            "filed_at": _now(),
        }
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
        out: list[ConsigneeReport] = []
        for consignee, shipped in sorted(state["shipments"].items()):
            account = state["accounts"].get(consignee, {})
            out.append(
                ConsigneeReport(
                    consignee=consignee,
                    shipped=int(shipped),
                    disposition=Disposition(
                        returned=int(account.get("returned", 0)),
                        destroyed=int(account.get("destroyed", 0)),
                        quarantined=int(account.get("quarantined", 0)),
                        dispensed=int(account.get("dispensed", 0)),
                    ),
                    attested_by=account.get("attested_by") or None,
                    claims_complete=bool(account.get("claims_complete", False)),
                )
            )
        return out
