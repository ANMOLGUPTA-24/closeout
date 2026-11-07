#!/usr/bin/env python3
"""Provision Closeout's rooms on a local Switch server.

Saves closeout.template.yaml to the server and runs it, which creates the
master recall room, one room per consignee, the registrar and the two
liaisons, and posts each room's kickoff.

    python3 scripts/provision.py            # save and run
    python3 scripts/provision.py --save-only

This starts real agent sessions on this machine, backed by whichever coding
agent the provider param resolves to.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CREDS = Path.home() / ".config" / "closeout" / "relay.json"
TEMPLATE = Path(__file__).resolve().parent.parent / "closeout.template.yaml"

TEMPLATE_NAME = "closeout-recall-room"
# Defaults match the demo the README and docs/DEMO.md walk through. Override
# them on the command line to provision a different recall.
RECALL_SLUG = "skinguard"
RECALL_NUMBER = "D-1572-2020"
PRODUCT = "SkinGuard 24 hand sanitizer, labelled to contain methanol (Class I)"


def load_creds() -> dict:
    if not CREDS.exists():
        sys.exit(
            f"No relay credentials at {CREDS}.\n"
            "Run scripts/register_relay.py first."
        )
    return json.loads(CREDS.read_text())


def op(creds: dict, name: str, payload: dict) -> dict:
    url = f"{creds['base_url']}/agents/{creds['agent_id']}/ops/{name}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        sys.exit(f"{name} failed ({exc.code}): {exc.read().decode()[:600]}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach the Switch server: {exc.reason}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-only", action="store_true")
    parser.add_argument("--recall-slug", default=RECALL_SLUG,
                        help=f"short slug used in every name it creates (default: {RECALL_SLUG})")
    parser.add_argument("--recall", default=RECALL_NUMBER,
                        help=f"the regulator's recall number (default: {RECALL_NUMBER})")
    parser.add_argument("--product", default=PRODUCT,
                        help="one line naming the recalled product and the hazard")
    args = parser.parse_args()

    creds = load_creds()
    document = TEMPLATE.read_text()

    existing = {
        t["name"]: t["id"] for t in op(creds, "list_templates", {}).get("result", [])
    }

    if TEMPLATE_NAME in existing:
        template_id = existing[TEMPLATE_NAME]
        op(
            creds,
            "update_template",
            {"template_id": template_id, "yaml": document},
        )
        print(f"Updated template {TEMPLATE_NAME} ({template_id})")
    else:
        saved = op(
            creds,
            "save_template",
            {
                "name": TEMPLATE_NAME,
                "description": (
                    "A recall room that cannot be closed by assertion: a "
                    "registrar, one isolated room per consignee, and an "
                    "exclusive regulatory role that alone may authorize closure."
                ),
                "yaml": document,
                "visibility": "private",
            },
        )
        template_id = saved.get("result", saved).get("id")
        print(f"Saved template {TEMPLATE_NAME} ({template_id})")

    if args.save_only:
        return 0

    result = op(
        creds,
        "run_template",
        {
            "template_id": template_id,
            "inputs": {
                "recall": args.recall_slug,
                "recall_number": args.recall,
                "product": args.product,
            },
        },
    )
    print(json.dumps(result, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
