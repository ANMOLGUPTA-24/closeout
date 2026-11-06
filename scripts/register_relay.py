#!/usr/bin/env python3
"""Register Closeout's relay bot with a local Switch server.

Switch has no scheduler and no inbound webhook: the docs say outright that
"Switch has no schedule of its own", and the generic-webhook platform is
still an open issue. So an outside event -- here, a recall notice from the
FDA's enforcement database -- reaches a room through a registered agent that
posts into it. That agent is this relay bot.

It needs no WebSocket. Registration returns an API key, and
``POST /agents/{id}/message`` posts into a room with it.

    python3 scripts/register_relay.py --name closeout-relay

Credentials are written to ~/.config/closeout/relay.json with mode 0600 and
are never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONSOLE_DIR = Path.home() / ".config" / "switchdash" / "local-switch-server"
CREDS = Path.home() / ".config" / "closeout" / "relay.json"


def discover_api_port() -> int:
    ports = json.loads((CONSOLE_DIR / "ports.json").read_text())
    return int(ports["api"])


def read_registration_token() -> str:
    """Read the token Console generated for its local server.

    Console owns this server, so its env file is the only place the token
    exists. Nothing here prints it.
    """
    env_path = CONSOLE_DIR / "native" / "run" / "switch-core.env"
    if not env_path.exists():
        sys.exit(
            f"No local server env at {env_path}.\n"
            "Is Switch Console running its server on this computer?"
        )
    for line in env_path.read_text().splitlines():
        if line.startswith("AGENT_REGISTRATION_TOKEN="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"No AGENT_REGISTRATION_TOKEN in {env_path}")


def post(url: str, payload: dict, token: str) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        sys.exit(f"{exc.code} from {url}: {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach {url}: {exc.reason}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="closeout-relay")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="re-register a name that already exists",
    )
    args = parser.parse_args()

    port = discover_api_port()
    base = f"http://127.0.0.1:{port}"
    token = read_registration_token()

    result = post(
        f"{base}/agents",
        {
            "name": args.name,
            "description": (
                "Posts recall notices from the FDA enforcement database into "
                "the recall room. Relays only; never decides anything."
            ),
            "connector_type": "closeout-relay",
            "integration_profile": {
                "connection_model": "always_on",
                "message_exchange": True,
                "pre_invocation_mediation": [],
                "post_invocation_mediation": [],
                "event_reporting": [],
            },
            "overwrite": args.overwrite,
        },
        token,
    )

    CREDS.parent.mkdir(parents=True, exist_ok=True)
    CREDS.write_text(
        json.dumps(
            {"base_url": base, "agent_id": result["id"], "api_key": result["api_key"]},
            indent=2,
        )
        + "\n"
    )
    os.chmod(CREDS, 0o600)

    print(f"Registered {args.name}")
    print(f"  agent id   {result['id']}")
    print(f"  server     {base}")
    print(f"  credentials {CREDS} (mode 0600, api key not printed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
