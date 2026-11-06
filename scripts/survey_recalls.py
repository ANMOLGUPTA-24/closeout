#!/usr/bin/env python3
"""Measure what the FDA enforcement record does and does not say.

The README claims that Class I recall records overwhelmingly state how
much product went out and never state how much came back. That is the
project's central factual claim, so here is the script that produces it:

    python3 scripts/survey_recalls.py                 # food, 3000 records
    python3 scripts/survey_recalls.py --kind drug --sample 1000

Needs network. openFDA requires no API key for this volume, and returns
404 rather than an empty list when nothing matches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

PAGE = 1000

#: Fields that would have to exist for a record to say how much came back.
RECOVERY_WORDS = ("recover", "return", "disposit", "reconcil", "destroy")


def fetch(kind: str, skip: int, limit: int) -> tuple[list[dict], int]:
    url = (
        f"https://api.fda.gov/{kind}/enforcement.json?search="
        + urllib.parse.quote('classification:"Class I"')
        + f"&limit={limit}&skip={skip}"
    )
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return [], 0
        raise
    return payload.get("results", []), payload["meta"]["results"]["total"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("food", "drug", "device"), default="food")
    parser.add_argument("--sample", type=int, default=3000)
    args = parser.parse_args()

    rows: list[dict] = []
    total = 0
    while len(rows) < args.sample:
        page, total = fetch(args.kind, len(rows), min(PAGE, args.sample - len(rows)))
        if not page:
            break
        rows += page

    if not rows:
        print("openFDA returned nothing; try again later.", file=sys.stderr)
        return 1

    def blank(value: object) -> bool:
        return not str(value or "").strip()

    numeric = sum(1 for r in rows if re.search(r"\d", str(r.get("product_quantity", ""))))
    missing = sum(1 for r in rows if blank(r.get("product_quantity")))
    unknown = sum(
        1
        for r in rows
        if re.search(r"unknown|undetermined", str(r.get("product_quantity", "")), re.I)
    )

    fields: set[str] = set()
    for row in rows:
        fields |= set(row)
    recovery_fields = sorted(
        f for f in fields if any(w in f.lower() for w in RECOVERY_WORDS)
    )

    pct = lambda n: f"{n / len(rows) * 100:.1f}%"  # noqa: E731

    print(f"openFDA {args.kind} enforcement, classification 'Class I'")
    print(f"  records in the database : {total}")
    print(f"  records sampled         : {len(rows)}")
    print()
    print(f"  state a numeric quantity shipped : {numeric} ({pct(numeric)})")
    print(f"  state nothing at all             : {missing} ({pct(missing)})")
    print(f"  say 'unknown'                    : {unknown} ({pct(unknown)})")
    print()
    print(f"  distinct fields across the sample: {len(fields)}")
    print(
        "  fields that could carry how much came back: "
        + (", ".join(recovery_fields) if recovery_fields else "NONE")
    )
    print()
    if not recovery_fields:
        print(
            "  So: the record says what went out, and has nowhere to say what\n"
            "  came back. That is a missing concept, not missing data."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
