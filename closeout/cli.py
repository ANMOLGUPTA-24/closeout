"""Closeout's command line: what the agents in the room actually run.

The registrar runs ``reconcile``. A liaison runs ``file``. Neither computes
anything; the arithmetic lives in closeout.recon and is plain code, so the
figures in the room are reproducible by anyone with the repo.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from closeout.recon import BUCKETS, reconcile
from closeout.store import RecallStore

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _fixture_for(recall_number: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in recall_number)
    return DATA_DIR / f"openfda-{safe}.json"


def _fmt_rate(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def cmd_reconcile(args: argparse.Namespace) -> int:
    store = RecallStore(args.recall, root=args.root)
    result = reconcile(args.recall, store.reports())

    if args.json:
        print(
            json.dumps(
                {
                    "recall_number": result.recall_number,
                    "shipped": result.shipped,
                    "accounted": result.accounted,
                    "unaccounted": result.unaccounted,
                    "recovered": result.recovered,
                    "recovery_rate": round(result.recovery_rate, 4),
                    "evidenced_recovered": result.evidenced_recovered,
                    "evidenced_recovery_rate": round(
                        result.evidenced_recovery_rate, 4
                    ),
                    "may_close": result.may_close,
                    "blockers": result.blockers(),
                    "findings": [
                        {
                            "consignee": f.consignee,
                            "severity": f.severity.value,
                            "code": f.code,
                            "detail": f.detail,
                        }
                        for f in result.findings
                    ],
                },
                indent=2,
            )
        )
        return 0 if result.may_close else 1

    print(f"Recall {result.recall_number}")
    print(f"  shipped       {result.shipped}")
    print(f"  accounted     {result.accounted}")
    print(f"  unaccounted   {result.unaccounted}")
    print(f"  recovered     {result.recovered}  ({_fmt_rate(result.recovery_rate)})")
    print(
        f"  evidenced     {result.evidenced_recovered}  "
        f"({_fmt_rate(result.evidenced_recovery_rate)} of shipped, "
        "recovery backed by a document)"
    )
    print()

    for report in result.reports:
        state = "no account filed" if not report.attested else report.attested_by
        print(
            f"  {report.consignee:<26} shipped {report.shipped:>6}  "
            f"unaccounted {report.outstanding:>6}  [{state}]"
        )
        gap = report.returns_gap
        if gap:
            print(
                f"  {'':<26} returns claimed "
                f"{report.disposition.returned.units}, firm logged "
                f"{report.independent_returns} (gap {gap:+d})"
            )
    print()

    if result.may_close:
        print("MAY CLOSE: every unit accounted for, every consignee attested.")
        print(
            f"Recovery rate {_fmt_rate(result.recovery_rate)} must be stated to "
            "@regulatory before closure is authorized."
        )
        return 0

    print("CLOSURE REFUSED")
    for blocker in result.blockers():
        print(f"  - {blocker}")
    return 1


def cmd_file(args: argparse.Namespace) -> int:
    store = RecallStore(args.recall, root=args.root)
    known = set(store.load()["shipments"])
    if args.consignee not in known:
        print(
            f"error: no shipment on record for {args.consignee!r}. "
            f"Known consignees: {', '.join(sorted(known)) or 'none'}",
            file=sys.stderr,
        )
        return 2

    counts = {bucket: getattr(args, bucket) for bucket in BUCKETS}
    evidence = {bucket: getattr(args, f"{bucket}_evidence") for bucket in BUCKETS}

    store.file_account(
        args.consignee,
        counts=counts,
        evidence=evidence,
        attested_by=args.attested_by,
        claims_complete=args.claims_complete,
    )
    uncited = [b for b in BUCKETS if counts[b] and not evidence[b]]
    print(f"Filed {args.consignee}'s account, attested by {args.attested_by}.")
    if uncited:
        print(f"  cites no document for: {', '.join(uncited)}")
    return cmd_reconcile(args)


def cmd_receipt(args: argparse.Namespace) -> int:
    """Record the firm's own receiving log for one consignee."""
    store = RecallStore(args.recall, root=args.root)
    store.record_receipt(args.consignee, args.units)
    print(
        f"Firm's receiving log: {args.units} units recorded back from "
        f"{args.consignee}."
    )
    return 0


def cmd_ship(args: argparse.Namespace) -> int:
    store = RecallStore(args.recall, root=args.root)
    store.set_shipment(args.consignee, args.units)
    print(f"Recorded {args.units} units shipped to {args.consignee}.")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    """Authorize closure. Refuses unless reconciliation permits it."""
    store = RecallStore(args.recall, root=args.root)
    result = reconcile(args.recall, store.reports())

    if not result.may_close:
        print("CLOSURE REFUSED. Outstanding:", file=sys.stderr)
        for blocker in result.blockers():
            print(f"  - {blocker}", file=sys.stderr)
        return 1

    store.record_closure(args.authorized_by, result.recovery_rate)
    print(
        f"Recall {args.recall} closed by {args.authorized_by}. "
        f"Recovery rate {_fmt_rate(result.recovery_rate)}; "
        f"{result.shipped - result.recovered} units were never recovered."
    )
    return 0


def cmd_certificate(args: argparse.Namespace) -> int:
    """Emit the closure certificate for a recall that has been closed.

    The registrar posts this into the room as a document rather than a
    message, because a chat message scrolls away and a recall's closure is
    the one thing someone will come looking for in two years.
    """
    store = RecallStore(args.recall, root=args.root)
    state = store.load()
    closure = state.get("closure")
    if not closure:
        print(
            f"error: recall {args.recall} has not been closed, so there is "
            "nothing to certify.",
            file=sys.stderr,
        )
        return 1

    result = reconcile(args.recall, store.reports())
    never = result.shipped - result.recovered
    lines = [
        f"# Closure certificate — recall {args.recall}",
        "",
        f"Closed by **{closure['authorized_by']}** at {closure['closed_at']}.",
        "",
        f"- Shipped: **{result.shipped}**",
        f"- Recovered: **{result.recovered}** ({_fmt_rate(result.recovery_rate)})",
        f"- Never recovered: **{never}**",
        "",
        "## What each consignee accounted for",
        "",
        "| Consignee | Shipped | Returned | Destroyed | Quarantined | Dispensed | Attested by |",
        "|---|---|---|---|---|---|---|",
    ]
    for report in result.reports:
        counts = " | ".join(
            str(getattr(report.disposition, bucket).units) for bucket in BUCKETS
        )
        lines.append(
            f"| {report.consignee} | {report.shipped} | {counts} | "
            f"{report.attested_by} |"
        )
    lines += [
        "",
        "## Evidence",
        "",
    ]
    for report in result.reports:
        for bucket in BUCKETS:
            count = getattr(report.disposition, bucket)
            if count.units:
                lines.append(
                    f"- {report.consignee}, {bucket} {count.units}: "
                    f"`{count.evidence}`"
                )
    log = state.get("receiving_log", {})
    if log:
        lines += ["", "## Firm's receiving log, cross-checked", ""]
        for consignee, units in sorted(log.items()):
            lines.append(f"- {consignee}: {units} units recorded arriving back")

    lines += [
        "",
        f"{never} units were never recovered. The FDA enforcement record for "
        f"{args.recall} has no field in which to say so.",
    ]
    print("\n".join(lines))
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Pull a real recall record from openFDA, or read the bundled fixture.

    The regulator's record supplies the recall's identity and hazard. It does
    not supply lot-to-consignee quantities -- real records frequently have an
    empty product_quantity and no lot code at all, which is a large part of
    why recalls cannot be reconciled today. Those quantities are synthetic
    here, and labelled as such.
    """
    if args.offline:
        fixture = _fixture_for(args.recall)
        if not fixture.exists():
            print(f"error: no bundled record at {fixture}", file=sys.stderr)
            return 2
        record = json.loads(fixture.read_text())
    else:
        import urllib.request

        # openFDA splits enforcement reports by product type, and the recall
        # number says which: D- for drugs, F- for food, Z- for devices.
        endpoint = {"D": "drug", "F": "food", "Z": "device"}.get(
            args.recall[:1].upper()
        )
        if endpoint is None:
            print(
                f"error: cannot tell which openFDA endpoint serves "
                f"{args.recall!r}; expected it to start with D-, F- or Z-.",
                file=sys.stderr,
            )
            return 2
        url = (
            f"https://api.fda.gov/{endpoint}/enforcement.json?search=recall_number:"
            f'"{args.recall}"&limit=1'
        )
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = json.load(response)
        except Exception as exc:  # network, rate limit, schema drift
            print(f"error: openFDA request failed: {exc}", file=sys.stderr)
            print("hint: re-run with --offline to use the bundled record.", file=sys.stderr)
            return 2
        results = payload.get("results") or []
        if not results:
            print(f"error: openFDA has no record for {args.recall}", file=sys.stderr)
            return 2
        record = results[0]

    for key in (
        "recall_number",
        "recalling_firm",
        "classification",
        "status",
        "product_description",
        "reason_for_recall",
        "distribution_pattern",
        "product_quantity",
        "code_info",
    ):
        value = str(record.get(key, "") or "(empty in the regulator's record)")
        print(f"{key}: {value[:160]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="closeout", description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="where recall state is stored (default: data/recalls)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("reconcile", help="reconcile a recall and decide closure")
    p.add_argument("--recall", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_reconcile)

    p = sub.add_parser("ship", help="record units shipped to a consignee")
    p.add_argument("--recall", required=True)
    p.add_argument("--consignee", required=True)
    p.add_argument("--units", type=int, required=True)
    p.set_defaults(func=cmd_ship)

    p = sub.add_parser("file", help="file a consignee's final account")
    p.add_argument("--recall", required=True)
    p.add_argument("--consignee", required=True)
    for bucket in BUCKETS:
        p.add_argument(f"--{bucket}", type=int, default=0)
        p.add_argument(
            f"--{bucket}-evidence",
            dest=f"{bucket}_evidence",
            default=None,
            help=f"document backing the {bucket} count, e.g. returns-receipt/RR-4471",
        )
    p.add_argument("--attested-by", dest="attested_by", required=True)
    p.add_argument(
        "--claims-complete",
        dest="claims_complete",
        action="store_true",
        help="the consignee asserts nothing is outstanding",
    )
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_file)

    p = sub.add_parser(
        "receipt",
        help="record the firm's own receiving log for a consignee",
    )
    p.add_argument("--recall", required=True)
    p.add_argument("--consignee", required=True)
    p.add_argument("--units", type=int, required=True)
    p.set_defaults(func=cmd_receipt)

    p = sub.add_parser("close", help="authorize closure (regulatory sign-off)")
    p.add_argument("--recall", required=True)
    p.add_argument("--authorized-by", dest="authorized_by", required=True)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser(
        "certificate",
        help="emit the closure certificate for a closed recall",
    )
    p.add_argument("--recall", required=True)
    p.set_defaults(func=cmd_certificate)

    p = sub.add_parser("fetch", help="show the regulator's record for a recall")
    p.add_argument("--recall", required=True)
    p.add_argument(
        "--offline",
        action="store_true",
        help="read the bundled openFDA record instead of the network",
    )
    p.set_defaults(func=cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
