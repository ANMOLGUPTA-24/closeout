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
RECALL="F-0616-2018"
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
F-0616-2018 is a real FDA Class I recall: Nyblad Orchards apples, possible
Listeria. The record says "5278 units shipped", lists eleven lot numbers,
and gives its status as Terminated.

What it does not say -- what the enforcement schema has no field for at
all -- is how many of those 5,278 units ever came back.
TXT
run fetch --recall "$RECALL" --offline

rule "Shipments on record (synthetic split of the real 5,278 units)"
run ship --recall "$RECALL" --consignee "Westside Distributors" --units 4278
run ship --recall "$RECALL" --consignee "Midtown Pharmacy" --units 1000

rule "Opening position: nobody has filed"
run reconcile --recall "$RECALL" || true

rule "Midtown files a clean, evidenced account"
run file --recall "$RECALL" --consignee "Midtown Pharmacy" \
  --returned 1000 --returned-evidence "returns-receipt/RR-5512" \
  --attested-by "R. Iyer, pharmacist-in-charge" || true

rule "REFUSAL 1 — Westside asserts the recall is complete"
cat <<'TXT'
Westside returns 2,878 of 4,278 units and states the recall is finished.
Nothing in the words is wrong. The arithmetic is.
TXT
refuse_or_die run file --recall "$RECALL" --consignee "Westside Distributors" \
  --returned 2878 --returned-evidence "returns-receipt/RR-4471" \
  --attested-by "D. Okafor, QA lead" --claims-complete
echo
echo ">> Refused. 1,400 Class I units are unaccounted for."

rule "REFUSAL 1b — regulatory sign-off is attempted anyway"
refuse_or_die run close --recall "$RECALL" --authorized-by "@regulatory"
echo
echo ">> Even the regulatory role cannot close it. Authority is not arithmetic."

rule "REFUSAL 2 — the account now balances, but rests on nothing"
cat <<'TXT'
Westside finds the rest: 900 destroyed on site, 300 quarantined off-sale,
200 sold and unrecoverable. 4,278 of 4,278 accounted for.

Only the returns cite a document. The destruction and the quarantine are
Westside's word.
TXT
refuse_or_die run file --recall "$RECALL" --consignee "Westside Distributors" \
  --returned 2878 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 900 --quarantined 300 \
  --dispensed 200 --dispensed-evidence "pos-export/2018-03-14" \
  --attested-by "D. Okafor, QA lead"
echo
echo ">> Refused. Adding up is not the same as being true."

rule "REFUSAL 3 — every count is evidenced, and one is still wrong"
cat <<'TXT'
Westside produces the destruction certificate and the quarantine log. Every
count now cites a document, and the total is exact.

Then the firm checks its own receiving log -- the other side of the
transaction -- and finds it recorded 2,600 units arriving back, not 2,878.
TXT
run receipt --recall "$RECALL" --consignee "Westside Distributors" --units 2600
refuse_or_die run file --recall "$RECALL" --consignee "Westside Distributors" \
  --returned 2878 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 900 --destroyed-evidence "destruction-cert/DC-118" \
  --quarantined 300 --quarantined-evidence "quarantine-log/Q-22" \
  --dispensed 200 --dispensed-evidence "pos-export/2018-03-14" \
  --attested-by "D. Okafor, QA lead"
echo
echo ">> Refused. Two records disagree by 278 units, and self-consistent"
echo "   arithmetic could never have found it."

rule "RUN A — the dispute is resolved, and the truth is worse"
cat <<'TXT'
The 278 units were never sent back. They were sold before the recall notice
reached the shop floor, and written up as returns afterwards.

They do not move from "returned" to "found". They move from "recovered" to
"in someone's kitchen".
TXT
run file --recall "$RECALL" --consignee "Westside Distributors" \
  --returned 2600 --returned-evidence "returns-receipt/RR-4471" \
  --destroyed 900 --destroyed-evidence "destruction-cert/DC-118" \
  --quarantined 300 --quarantined-evidence "quarantine-log/Q-22" \
  --dispensed 478 --dispensed-evidence "pos-export/2018-03-14" \
  --attested-by "D. Okafor, QA lead"

rule "RUN A — closure authorized, with the recovery rate stated"
run close --recall "$RECALL" --authorized-by "M. Haddad, regulatory affairs"

rule "What was signed for"
cat <<'TXT'
4,500 of 5,278 units recovered: 85.3%. Every one of them backed by a
document.

778 units were never recovered -- 300 still held off-sale, and 478 eaten or
in a fridge somewhere. The cross-check moved 278 of those out of the
recovered column, where self-consistent arithmetic had been happy to leave
them.

That is the number a recall should be closed on, and the FDA enforcement
record has nowhere to put it.
TXT
