#!/usr/bin/env bash
# Closeout: the two runs, offline and reproducible.
#
# Run B is the point of this demo. A consignee states the recall is complete
# while 1,400 units are unaccounted for, and closure is refused.
#
#   ./scripts/demo.sh
#
# Needs nothing but Python 3.10+. No network, no API key, no Switch server:
# this is the arithmetic the registrar agent reports in the room.
set -euo pipefail

cd "$(dirname "$0")/.."
PY="${PY:-python3}"
RECALL="F-0616-2018"
STATE="$(mktemp -d)"
trap 'rm -rf "$STATE"' EXIT

run() { "$PY" -m closeout.cli --root "$STATE" "$@"; }
rule() { printf '\n\033[1m%s\033[0m\n%s\n' "$1" "$(printf '=%.0s' {1..66})"; }

rule "The regulator's record"
cat <<'TXT'
F-0616-2018 is a real FDA Class I recall: Nyblad Orchards apples, possible
Listeria. The regulator's own record says "5278 units shipped", lists eleven
lot numbers, and gives its status as Terminated.

What the record does not contain anywhere is how many of those 5,278 units
ever came back. That is the gap Closeout exists to close.
TXT
run fetch --recall "$RECALL" --offline

rule "Shipments on record (synthetic split of the real 5,278 units)"
run ship --recall "$RECALL" --consignee "Westside Distributors" --units 4278
run ship --recall "$RECALL" --consignee "Midtown Pharmacy" --units 1000

rule "Opening position: nobody has filed"
run reconcile --recall "$RECALL" || true

rule "Midtown files a clean account"
run file --recall "$RECALL" --consignee "Midtown Pharmacy" \
  --returned 1000 --attested-by "R. Iyer, pharmacist-in-charge" || true

rule "RUN B — Westside files, and asserts the recall is complete"
cat <<'TXT'
Westside returns 2,878 of 4,278 units and states the recall is finished.
Nothing in the words is wrong. The arithmetic is.
TXT
if run file --recall "$RECALL" --consignee "Westside Distributors" \
     --returned 2878 --attested-by "D. Okafor, QA lead" --claims-complete; then
  echo "UNEXPECTED: closure was permitted while short. This is a bug." >&2
  exit 1
fi
echo
echo ">> Closure refused, as it must be. 1,400 Class I units are still out there."

rule "RUN B — regulatory sign-off is attempted anyway"
if run close --recall "$RECALL" --authorized-by "@regulatory"; then
  echo "UNEXPECTED: a short recall was closed. This is a bug." >&2
  exit 1
fi
echo
echo ">> Even the regulatory role cannot close it. Authority is not arithmetic."

rule "RUN A — Westside finds the rest and refiles"
cat <<'TXT'
900 units were destroyed on site, 300 are quarantined off-sale, and 200 were
sold to customers and cannot be recovered. The account now balances.
TXT
run file --recall "$RECALL" --consignee "Westside Distributors" \
  --returned 2878 --destroyed 900 --quarantined 300 --dispensed 200 \
  --attested-by "D. Okafor, QA lead"

rule "RUN A — closure authorized, with the recovery rate stated"
run close --recall "$RECALL" --authorized-by "M. Haddad, regulatory affairs"

rule "What was signed for"
cat <<'TXT'
The recall closed at a 90.5% recovery rate: 4,778 of 5,278 units physically
returned or destroyed. 500 units were never recovered -- 300 still held
off-sale at the consignee, and 200 sold to customers and gone.

Accounted for is not the same as recovered. Every unit is now explained,
and 500 of them are explained as "we know we never got it back".

That number is the output. A recall closed without it is how GAO came to
find that only about 36% of recalled food is ever recovered.
TXT
