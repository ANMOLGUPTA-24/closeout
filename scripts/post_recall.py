#!/usr/bin/env python3
"""Post a recall notice from the FDA enforcement database into a room.

This is the outside event arriving. Switch has no scheduler and no inbound
webhook, so a registered agent posting on its own behalf is how an external
system reaches a room. The relay states facts from the regulator's record
and asks the registrar to open the recall; it decides nothing itself.

    python3 scripts/post_recall.py --room recall-nyblad --recall F-0616-2018

Add --live to fetch from openFDA instead of the bundled record.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CREDS = Path.home() / ".config" / "closeout" / "relay.json"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_creds() -> dict:
    if not CREDS.exists():
        sys.exit(f"No relay credentials at {CREDS}. Run scripts/register_relay.py.")
    return json.loads(CREDS.read_text())


def call(creds: dict, path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{creds['base_url']}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        sys.exit(f"{path} failed ({exc.code}): {exc.read().decode()[:500]}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach the Switch server: {exc.reason}")


def recall_record(number: str, live: bool) -> dict:
    if not live:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in number)
        fixture = DATA_DIR / f"openfda-{safe}.json"
        if not fixture.exists():
            sys.exit(f"No bundled record at {fixture}; try --live.")
        return json.loads(fixture.read_text())

    url = (
        "https://api.fda.gov/food/enforcement.json?"
        f'search=recall_number:"{number}"&limit=1'
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        results = json.load(response).get("results") or []
    if not results:
        sys.exit(f"openFDA has no record for {number}")
    return results[0]


def notice(record: dict, registrar: str) -> str:
    quantity = record.get("product_quantity") or "not stated in the record"
    lots = (record.get("code_info") or "not stated in the record").strip()
    return "\n".join(
        [
            f"**Recall {record.get('recall_number')}** — "
            f"{record.get('classification')}, "
            f"status *{record.get('status')}* in the FDA enforcement database.",
            "",
            f"- **Firm:** {record.get('recalling_firm')}",
            f"- **Product:** {(record.get('product_description') or '')[:200]}",
            f"- **Reason:** {(record.get('reason_for_recall') or '')[:240]}",
            f"- **Quantity:** {quantity}",
            f"- **Lots:** {lots[:240]}",
            f"- **Distribution:** {record.get('distribution_pattern')}",
            "",
            "The regulator's record states what went out. It states nothing "
            "about how much came back, and there is no field in it that "
            "would.",
            "",
            f"@{registrar}: open this recall and post the position.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--room", required=True, help="room name, e.g. recall-nyblad")
    parser.add_argument("--recall", required=True)
    parser.add_argument("--registrar", default="nyblad-registrar")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    creds = load_creds()
    record = recall_record(args.recall, args.live)

    rooms = call(creds, f"/agents/{creds['agent_id']}/ops/list_rooms", {})
    candidates = [
        r
        for r in (rooms.get("result") or rooms.get("rooms") or [])
        if r.get("name") == args.room
    ]
    if not candidates:
        available = ", ".join(
            sorted(
                str(r.get("name"))
                for r in (rooms.get("result") or rooms.get("rooms") or [])
            )
        )
        sys.exit(
            f"The relay is not in a room called {args.room!r}.\n"
            f"Rooms it can see: {available or '(none)'}\n"
            f"Invite it by typing  !invite-agent @closeout-relay  in the room."
        )

    room_id = candidates[0]["room_id"]

    # Not an agent operation: operations run inside a live MCP session, and
    # a relay has none. `POST /agents/{id}/message` is the connectionless
    # door, which is exactly what an outside event needs. The body @-mentions
    # the registrar, because an agent does not act on a message nobody
    # addressed to it.
    call(
        creds,
        f"/agents/{creds['agent_id']}/message",
        {"room_id": room_id, "content": notice(record, args.registrar)},
    )
    print(f"Posted recall {args.recall} into {args.room}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
