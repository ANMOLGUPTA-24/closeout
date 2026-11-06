#!/usr/bin/env python3
"""Tear down a previous Closeout run, through the gateway API.

Re-running the template collides with its own leftovers: Switch refuses an
agent name that already exists, and deleting a room in Console leaves the
Mattermost channel, so repeated runs accumulate duplicates. Clearing that
by hand is a dozen clicks each time. This does it in one call:

    python3 scripts/console_provision.py --clean-only --clean skinguard

**What this cannot do.** Creating the *agents* still needs Switch Console.
`/rooms/from-yaml` provisions rooms and groups and rejects a document with
an `agents:` block ("Unknown top-level key(s): agents"), and a managed
agent — one with a provider, a machine and a working directory — is
created by Console's own process, which pulls assignments from the server
rather than being driven by it. The hosted-machine routes are for SSH and
cloud hosts, not for the computer Console is running on. So the template
itself is run from Console's Templates view, and this script is for the
cleanup either side of it.

Credentials come from the local server's own env file, which Console
generated. Nothing is printed.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONSOLE_DIR = Path.home() / ".config" / "switchdash" / "local-switch-server"
TEMPLATE = Path(__file__).resolve().parent.parent / "closeout.template.yaml"


def console_env() -> dict[str, str]:
    path = CONSOLE_DIR / "native" / "run" / "switch-core.env"
    if not path.exists():
        sys.exit(
            f"No local server env at {path}.\n"
            "Is Switch Console running its server on this computer?"
        )
    out = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            out[key.strip()] = value.strip()
    return out


def gateway_base() -> str:
    """Where the gateway API lives.

    Not the `gateway` port, which serves the operator frontend: the API is
    mounted under /gateway on the main API port.
    """
    ports = json.loads((CONSOLE_DIR / "ports.json").read_text())
    return f"http://127.0.0.1:{int(ports['api'])}/gateway"


class Gateway:
    """The gateway API, signed in as the person who owns this server."""

    def __init__(self, base: str) -> None:
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def call(
        self, method: str, path: str, payload: dict | None = None
    ) -> tuple[int, object]:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.base}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        try:
            with self.opener.open(request, timeout=180) as response:
                body = response.read().decode()
                return response.status, (json.loads(body) if body else None)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            try:
                return exc.code, json.loads(body)
            except ValueError:
                return exc.code, body[:500]
        except urllib.error.URLError as exc:
            sys.exit(f"Could not reach the gateway at {self.base}: {exc.reason}")

    def login(self, email: str, password: str) -> None:
        status, body = self.call("POST", "/auth/login", {"email": email, "password": password})
        if status != 200:
            sys.exit(f"Gateway login failed ({status}): {body}")


def names_of(rows: object) -> list[dict]:
    if isinstance(rows, dict):
        for key in ("items", "results", "agents", "rooms", "data"):
            if isinstance(rows.get(key), list):
                return rows[key]
        return []
    return rows if isinstance(rows, list) else []


def clean(gw: Gateway, slug: str) -> None:
    """Remove the agents and rooms a previous run of this template made."""
    _, rooms = gw.call("GET", "/rooms")
    for room in names_of(rooms):
        name = str(room.get("name", ""))
        if name == f"recall-{slug}" or name.startswith(f"recall-{slug}-"):
            status, _ = gw.call("DELETE", f"/rooms/{room['id']}")
            print(f"  deleted room {name} ({status})")

    _, agents = gw.call("GET", "/agents")
    for agent in names_of(agents):
        name = str(agent.get("name", ""))
        if name.startswith(f"{slug}-"):
            status, _ = gw.call("DELETE", f"/agents/{agent['id']}")
            print(f"  deleted agent {name} ({status})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recall-slug", required=True, help="e.g. skinguard")
    parser.add_argument("--recall", required=True, help="e.g. D-1572-2020")
    parser.add_argument("--product", required=True)
    parser.add_argument(
        "--project-dir",
        default=str(TEMPLATE.parent),
        help="the clone the agents work in",
    )
    parser.add_argument(
        "--clean",
        action="append",
        default=[],
        metavar="SLUG",
        help="delete the rooms and agents of an earlier run (repeatable)",
    )
    parser.add_argument("--clean-only", action="store_true")
    args = parser.parse_args()

    env = console_env()
    gw = Gateway(gateway_base())
    gw.login(env["GATEWAY_ADMIN_EMAIL"], env["GATEWAY_ADMIN_PASSWORD"])
    print(f"Signed in to the gateway as {env['GATEWAY_ADMIN_EMAIL']}.")

    for slug in [*args.clean, *( [args.recall_slug] if not args.clean_only else [] )]:
        print(f"Cleaning {slug}:")
        clean(gw, slug)

    if args.clean_only:
        return 0

    status, body = gw.call(
        "POST",
        "/rooms/from-yaml",
        {
            "yaml": TEMPLATE.read_text(),
            "template_name": "closeout-recall-room",
            "inputs": {
                "recall": args.recall_slug,
                "recall_number": args.recall,
                "product": args.product,
                "project_dir": args.project_dir,
            },
        },
    )
    if status != 201:
        print(f"Provisioning failed ({status}):", file=sys.stderr)
        print(json.dumps(body, indent=2)[:2000], file=sys.stderr)
        return 1

    rooms = body.get("rooms") if isinstance(body, dict) else None
    print("Provisioned:")
    for room in rooms or []:
        print(f"  room {room.get('name')}")
    if not rooms:
        print(json.dumps(body, indent=2)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
