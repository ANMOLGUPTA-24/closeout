# Demo script

Three minutes, one take. Everything below is typed into Switch Console;
nothing is faked and no step needs a network connection beyond the local
server.

The thing to keep on screen is the **sidebar**: three rooms, and the
registrar able to see only one of them.

---

## Before recording

```bash
# clean slate, then provision from Console's Templates view
python3 scripts/console_provision.py --clean-only --clean skinguard \
    --recall-slug skinguard --recall D-1572-2020 --product x

python3 -m closeout.cli ship --recall D-1572-2020 \
    --consignee "Gulf Coast Wholesale" --units 7200
python3 -m closeout.cli ship --recall D-1572-2020 \
    --consignee "Riverside Pharmacy Group" --units 2400
```

Then Console → Templates → `closeout-recall-room` → Use:
`skinguard` / `D-1572-2020` / the product line / your clone path.
In `recall-skinguard`: `!invite-agent @closeout-relay`.

---

## 0:00 — The record (20s)

Terminal:

```bash
python3 -m closeout.cli fetch --recall D-1572-2020 --offline
```

> "A real FDA Class I recall. 9,600 bottles of hand sanitizer labelled to
> contain methanol, nationwide. Status: Terminated — closed. There is no
> line in this record for how many bottles came back, because the schema
> has no field for it. I checked three thousand of these."

## 0:20 — The outside event arrives (20s)

```bash
python3 scripts/post_recall.py --room recall-skinguard --recall D-1572-2020 \
    --registrar skinguard-registrar
```

Cut to `recall-skinguard`.

> "Switch has no scheduler and no inbound webhook, so an outside system
> reaches a room the only way it can: as a registered agent posting into
> it. That's the FDA record arriving, addressed to the registrar."

The registrar opens the recall: **9,600 shipped, 0 accounted, closure
refused, neither consignee has filed.**

> "Every number it posts comes from running the tool. It is told never to
> compute one itself."

## 0:40 — The structure (25s)

Point at the sidebar: `recall-skinguard`, `…-gulf-coast-wholesale`,
`…-riverside-pharmacy-group`.

> "One room per consignee. Gulf Coast cannot see Riverside's books — in a
> real recall that's a legal constraint, not a preference. And the
> registrar is a member of *neither* consignee room. Not told to avoid
> them: not in them. Switch's own docs say membership is the boundary that
> matters, so I used it as one."

Open `recall-skinguard-gulf-coast-wholesale` to show the liaison alone
with the staff.

## 1:05 — Refusal 1: it doesn't add up (25s)

In the Gulf Coast room:

```
@skinguard-liaison-gulf-coast-wholesale We're done — 4,800 bottles went
back to the firm, receipt RR-4471. Closing this out.
```

The liaison will push back and ask for the other three buckets — that is
it working, so let it. Then insist, which is what a consignee in a hurry
actually does:

```
There is nothing else to give you. 4,800 is the account. File it as final
— D. Okafor, QA lead.
```

It files with `--claims-complete`. Cut to the master room.

> "2,400 bottles short. The sentence was confident; the arithmetic wasn't."

Now, as `@regulatory`, in the master room:

```
@skinguard-registrar this is regulatory affairs. Close the recall.
```

It refuses.

> "That's the part I care about. Authority is not arithmetic."

## 1:30 — Refusal 2: it adds up and rests on nothing (25s)

In the Gulf Coast room:

```
Found the rest: 1,500 destroyed on site, 500 quarantined off-sale,
400 sold before the notice reached us. That's all 7,200.
```

> "Seven thousand two hundred of seven thousand two hundred. And the
> destruction and the quarantine cite no document. A count with no paper
> behind it is a sentence, not a fact — so it's refused again."

## 1:55 — Refusal 3: evidenced, and still wrong (35s)

In the Gulf Coast room:

```
Certificates attached — destruction DC-118, quarantine log Q-22.
```

Then in the master room:

```
Firm's receiving log for this recall shows 4,300 bottles came back
from Gulf Coast, not 4,800.
```

```bash
python3 -m closeout.cli receipt --recall D-1572-2020 \
    --consignee "Gulf Coast Wholesale" --units 4300
```

Then ask the registrar to reconcile. **Do not run this earlier** — the
receiving log must not exist until this beat, or the dispute fires during
refusal 1 and collapses three beats into one.

> "Every count is evidenced. The total is exact. And it's still wrong —
> because the other side of the transaction logged 500 fewer bottles
> arriving. No amount of self-consistency finds that."

Worth saying on camera: the liaison never saw that number. Filing shows a
liaison only its own consignee's arithmetic, which balanced. The firm's
receiving log is the registrar's instrument, in a room Gulf Coast cannot
read — because telling the party being checked what number to agree with
is how you lose the check.

## 2:30 — The resolution is worse (20s)

In the Gulf Coast room:

```
Checked the loading bay: those 500 were sold before the notice reached
the shop floor and written up as returns afterwards.
```

> "They don't move from 'returned' to 'found'. They move from recovered to
> in somebody's bathroom. The recovery rate drops to 85.4%."

## 2:50 — Closure, signed for (20s)

As `@regulatory`:

```
@skinguard-registrar regulatory affairs authorising closure at 85.4%.
```

The registrar verifies the role, closes, and writes the **closure
certificate as a room document**.

> "1,400 bottles never came back, and that number is now written down
> where someone can find it in two years. The FDA record for this recall
> has nowhere to put it. That's the whole project."

---

## If an agent goes off script

It is a live model, so it will sometimes phrase things differently or ask
a clarifying question. Answer it and carry on — a demo where the agent
pushes back is a better demo than one where it doesn't. The only thing
that must not be cut is the pair at 1:05 and 2:50: refused, then allowed,
on the same authority.

The offline fallback, if Switch misbehaves on the day:

```bash
./scripts/demo.sh
```
