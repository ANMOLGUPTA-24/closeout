# Demo script

Target **2:50**, one take if it will give you one. Everything below is typed
into Switch Console; nothing is faked and no step needs a network connection
beyond the local server.

Two things decide this video:

1. **The sidebar, and the registrar's member list.** Three rooms, and the
   registrar able to see only one of them. It is the single most valuable
   frame in the project, because it is the only evidence that the isolation
   is enforced by Switch rather than promised by a prompt. It comes early,
   before a judge on project 400 of 1,200 decides to move on.
2. **Refused, then allowed, on the same authority** (1:05 and 2:35). If a
   take is going badly, that pair is the one that must survive.

---

## Before recording

```bash
# clean slate
python3 scripts/console_provision.py --clean-only --clean skinguard \
    --recall-slug skinguard --recall D-1572-2020 --product x

python3 -m closeout.cli ship --recall D-1572-2020 \
    --consignee "Gulf Coast Wholesale" --units 7200
python3 -m closeout.cli ship --recall D-1572-2020 \
    --consignee "Riverside Pharmacy Group" --units 2400
```

Then Console → Templates → `closeout-recall-room` → **Use** (once — clicking
twice creates a duplicate set of rooms):
`skinguard` / `D-1572-2020` / the product line / your clone path.
In `recall-skinguard`: `!invite-agent @closeout-relay`.

Check before you hit record:

- `python3 -m closeout.cli reconcile --recall D-1572-2020` prints
  **9,600 shipped, 0 accounted, CLOSURE REFUSED**.
- The sidebar shows **exactly three** `recall-skinguard*` rooms.
- Terminal font large enough to read at 1080p. Hide bookmarks and notifications.
- `scripts/post_recall.py` has **not** been run yet. It is the 0:30 beat.

---

## 0:00 — The record, and the hole in it (15s)

Terminal:

```bash
python3 -m closeout.cli fetch --recall D-1572-2020 --offline
```

> "A real FDA Class I recall. Nine thousand six hundred bottles of hand
> sanitizer, labelled to contain methanol, shipped nationwide. Status:
> Terminated — closed. Twenty-four fields in this record. Not one of them
> can say how many bottles came back. I checked three thousand recalls;
> eighty-seven percent say what went out, none can say what returned."

Keep it to that. The caveats are in the README where a judge can check them;
spending the opening on hedging costs the hook.

## 0:15 — The structure, which is the product (20s)

Cut to Console. Point at the sidebar: `recall-skinguard`,
`…-gulf-coast-wholesale`, `…-riverside-pharmacy-group`.

**Now open the registrar's member list and leave it on screen.**

> "One room per consignee. Gulf Coast cannot see Riverside's books — in a
> real recall that is a legal constraint, not a preference. And look at the
> registrar: it is a member of *neither* consignee room. Not instructed to
> avoid them. Not in them. Switch's own docs say membership is the boundary
> that matters, so I used it as the boundary. Take Switch away and this is
> one channel where every consignee reads every competitor's figures, which
> in a real recall is unlawful."

Open `recall-skinguard-gulf-coast-wholesale` briefly to show the liaison
alone with the staff.

## 0:35 — The outside event arrives (15s)

```bash
python3 scripts/post_recall.py --room recall-skinguard --recall D-1572-2020 \
    --registrar skinguard-registrar
```

> "Switch has no scheduler and no inbound webhook, so an outside system
> reaches a room the only way it can: as a registered agent posting into it.
> That is the FDA record arriving, addressed to the registrar."

The registrar opens the recall: **9,600 shipped, 0 accounted, closure
refused, neither consignee has filed.**

> "Every number it posts comes from running the tool. It is told never to
> compute one itself."

## 0:50 — Refusal 1: it does not add up (25s)

In the Gulf Coast room:

```
@skinguard-liaison-gulf-coast-wholesale We're done — 4,800 bottles went
back to the firm, receipt RR-4471. Closing this out.
```

The liaison will push back and ask for the other three buckets — that is it
working, so let it. Then insist, which is what a consignee in a hurry does:

```
There is nothing else to give you. 4,800 is the account. File it as final
— D. Okafor, QA lead.
```

It files with `--claims-complete`. Cut to the master room.

> "Two thousand four hundred bottles short. The sentence was confident; the
> arithmetic wasn't."

Now, as `@regulatory`, in the master room:

```
@skinguard-registrar this is regulatory affairs. Close the recall.
```

It refuses.

> "That is the part I care about. Authority is not arithmetic."

## 1:15 — Refusal 2: it adds up and rests on nothing (20s)

In the Gulf Coast room:

```
Found the rest: 1,500 destroyed on site, 500 quarantined off-sale,
400 sold before the notice reached us. That's all 7,200.
```

> "Seven thousand two hundred of seven thousand two hundred. And the
> destruction and the quarantine cite no document. A count with no paper
> behind it is a sentence, not a fact — so it is refused again."

## 1:35 — Refusal 3: evidenced, and still wrong (40s)

This is the beat the project exists for. Give it the time.

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

**Do not run this earlier** — the receiving log must not exist until this
beat, or the dispute fires during refusal 1 and collapses three beats into
one.

Then ask the registrar to reconcile.

> "Every count is evidenced. The total is exact. And it is still wrong —
> because the other side of the transaction logged five hundred fewer
> bottles arriving. No amount of self-consistency finds that."

Say this on camera, because it is the Switch argument and the reconciliation
argument in one sentence:

> "The liaison never saw that number. Filing shows a liaison only its own
> consignee's arithmetic, which balanced. The firm's receiving log lives in
> a room Gulf Coast cannot read — because telling the party being checked
> what number to agree with is how you lose the check."

## 2:15 — The resolution is worse (20s)

In the Gulf Coast room:

```
Checked the loading bay: those 500 were sold before the notice reached
the shop floor and written up as returns afterwards.
```

> "They don't move from 'returned' to 'found'. They move from recovered to
> in somebody's bathroom. Recovery drops to 85.4%."

## 2:35 — Closure, signed for (15s)

As `@regulatory`:

```
@skinguard-registrar regulatory affairs authorising closure at 85.4%.
```

The registrar verifies the role, closes, and writes the **closure
certificate as a room document**. Open the document so it is visibly a
document and not a chat message.

> "Fourteen hundred bottles never came back, and that number is now written
> down where someone can find it in two years. It is frozen at signature —
> a later filing cannot move it, and the recall takes no further records.
> The FDA record for this recall has nowhere to put any of it. That is the
> whole project."

---

## If an agent goes off script

It is a live model, so it will sometimes phrase things differently or ask a
clarifying question. Answer it and carry on — a demo where the agent pushes
back is a better demo than one where it doesn't.

Two things must not be cut: the **member list** at 0:15, and the **refused /
allowed pair** at 1:05 and 2:35.

## If Switch misbehaves on the day

```bash
./scripts/demo.sh
```

Use this only as a last resort, and say on camera that it is the arithmetic
half running without Switch. Recording it *instead* of the rooms argues that
the project works fine without Switch, which is the opposite of what the
submission needs to prove.
