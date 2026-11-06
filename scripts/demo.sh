#!/usr/bin/env bash
# Closeout: the whole story, offline and reproducible.
#
#   ./scripts/demo.sh
#
# Needs nothing but Python 3.10+. No network, no API key, no Switch server:
# this is the arithmetic the registrar agent reports in the room.
#
# Three refusals, each catching something the previous one could not:
#   1. the numbers do not add up
#   2. the numbers add up but rest on nothing
#   3. the numbers add up, are evidenced, and disagree with the firm's own
#      receiving log
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PY:-python3}"
RECALL="D-1572-2020"
WEST="Gulf Coast Wholesale"
EAST="Riverside Pharmacy Group"
STATE="$(mktemp -d)"
trap 'rm -rf "$STATE"' EXIT

run() { "$PY" -m closeout.cli --root "$STATE" "$@"; }
rule() { printf '\n\033[1m%s\033[0m\n%s\n' "$1" "$(printf '=%.0s' {1..70})"; }
refuse_or_die() {
  if "$@"; then
    echo "UNEXPECTED: closure was permitted. This is a bug." >&2
    exit 1
  fi
}

rule "The regulator's record"
cat <<'TXT'
D-1572-2020 is a real FDA Class I drug recall: SkinGuard 24 hand sanitizer,
9,600 bottles, distributed nationwide. Status: Terminated.

Be precise about what it is. The firm declared the methanol -- the recall
reason is an unapproved-drug and labelling violation, not a contamination
scandal. FDA made it Class I anyway, because methanol has no business in
something rubbed on skin all day. (Separately that year, CDC reviewed 15
hospitalisations from people *drinking* methanol-containing sanitizers:
four died, three were discharged with vision impairment. Other products,
other firms. Nothing attributes harm to these 9,600 bottles.)

That ordinariness is the point. This is a routine Class I recall, and even
a routine one was closed without anyone recording what came back.

Because the record cannot say it. The schema has no field for it.
TXT
run fetch --recall "$RECALL" --offline

rule "Shipments on record (synthetic split of the real 9,600 bottles)"
run ship --recall "$RECALL" --consignee "$WEST" --units 7200
run ship --recall "$RECALL" --consignee "$EAST" --units 2400

rule "Opening position: nobody has filed"
run reconcile --recall "$RECALL" || true

rule "Riverside files a clean, evidenced account"
run file --recall "$RECALL" --consignee "$EAST" \
  --returned 2400 --returned-evidence "returns-receipt/RR-5512" \
  --attested-by "R. Iyer, pharmacist-in-charge" || true

rule "REFUSAL 1 — Gulf Coast asserts the recall is complete"
cat <<'TXT'
Gulf Coast returns 4,800 of 7,200 bottles and states the recall is
finished. Nothing in the words is wrong. The arithmetic is.
TXT
refuse_or_die run file --recall "$RECALL" --consignee "$WEST" \
  --returned 4800 --returned-evidence "returns-receipt/RR-4471" \
  --attested-by "D. Okafor, QA lead" --claims-complete
echo
echo ">> Refused. 2,400 bottles of methanol-labelled sanitizer are unaccounted for."

rule "REFUSAL 1b — regulatory sign-off is attempted anyway"
refuse_or_die run close --recall "$RECALL" --authorized-by "@regulatory"
echo
echo ">> Even the regulatory role cannot close it. Authority is not arithmetic."

rule "REFUSAL 2 — the account now balances, but rests on nothing"
cat <<'TXT'
Gulf Coast finds the rest: 1,500 destroyed on site, 500 quarantined
off-sale, 400 sold and unrecoverable. 7,200 of 7,200 accounted for.

Only the returns cite a document. The destruction and the quarantine are
Gulf Coast's word.
TXT
refuse_or_die run file --recall "$RECALL" --consignee "$WEST" \
  --returned 4800 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 1500 --quarantined 500 \
  --dispensed 400 --dispensed-evidence "pos-export/2020-08-20" \
  --attested-by "D. Okafor, QA lead"
echo
echo ">> Refused. Adding up is not the same as being true."

rule "REFUSAL 3 — every count is evidenced, and one is still wrong"
cat <<'TXT'
Gulf Coast produces the destruction certificate and the quarantine log.
Every count now cites a document, and the total is exact.

Then the firm checks its own receiving log -- the other side of the
transaction -- and finds it recorded 4,300 bottles arriving back, not 4,800.
TXT
run receipt --recall "$RECALL" --consignee "$WEST" --units 4300
refuse_or_die run file --recall "$RECALL" --consignee "$WEST" \
  --returned 4800 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 1500 --destroyed-evidence "destruction-cert/DC-118" \
  --quarantined 500 --quarantined-evidence "quarantine-log/Q-22" \
  --dispensed 400 --dispensed-evidence "pos-export/2020-08-20" \
  --attested-by "D. Okafor, QA lead"
echo
echo ">> Refused. Two records disagree by 500 bottles, and self-consistent"
echo "   arithmetic could never have found it."

rule "RUN A — the dispute is resolved, and the truth is worse"
cat <<'TXT'
The 500 bottles were never sent back. They were sold before the recall
notice reached the shop floor, and written up as returns afterwards.

They do not move from "returned" to "found". They move from "recovered" to
"in somebody's bathroom".
TXT
run file --recall "$RECALL" --consignee "$WEST" \
  --returned 4300 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 1500 --destroyed-evidence "destruction-cert/DC-118" \
  --quarantined 500 --quarantined-evidence "quarantine-log/Q-22" \
  --dispensed 900 --dispensed-evidence "pos-export/2020-08-20" \
  --attested-by "D. Okafor, QA lead"

rule "RUN A — closure authorized, with the recovery rate stated"
run close --recall "$RECALL" --authorized-by "M. Haddad, regulatory affairs"

rule "What was signed for"
cat <<'TXT'
8,200 of 9,600 bottles recovered: 85.4%. Every one of them backed by a
document.

1,400 bottles were never recovered -- 500 still held off-sale, and 900 sold
to people who have them at home. The cross-check moved 500 of those out of
the recovered column, where self-consistent arithmetic had been happy to
leave them.

That is the number a recall should be closed on. The FDA enforcement
record has nowhere to put it, and this recall's status is Terminated.
TXT
