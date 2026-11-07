# The agent that cannot be talked into it: building a recall registrar on Switch

*A product recall is closed by reconciliation, never by assertion. Here is how
I built an agent that refuses to close one — and the five things about Switch
that cost me an afternoon each, so they cost you nothing.*

---

## Short version

- **The problem:** FDA enforcement records have 24 fields. `product_quantity`
  says what shipped. **Nothing says what came back.** I sampled 3,000 Class I
  food recalls: 86.9% state a quantity shipped, none can state a quantity
  recovered.
- **What I built:** `Closeout`, a Switch room where a registrar agent holds a
  recall open until every unit is accounted for, every count cites a document,
  and nothing contradicts the firm's own receiving log.
- **The Switch part:** one private room per consignee, and the registrar is a
  member of **none of them**. It is not instructed to keep secrets. It is
  structurally unable to read them.
- **The result:** a demo recall closes at **85.4%**, not the 90.6% its own
  arithmetic was happy with — because the cross-check found 500 bottles that
  were never received.
- **Reproduce it in 30 seconds:** `git clone … && ./scripts/demo.sh`. No
  network, no API key, no Switch server, pure standard library.

---

## The hole in the record

Pick any recall. Here is a real one — `D-1572-2020`, a Class I drug recall:
9,600 bottles of hand sanitizer labelled to contain methanol, shipped
nationwide. Status: **Terminated**. Closed.

How many bottles came back?

The record cannot say. Not "the field is blank" — there is no field. I pulled
the openFDA enforcement schema and counted: 24 fields, and the only quantity in
them is `product_quantity`, which is shipped-side. So I sampled 3,000 Class I
food recalls:

```
  state a numeric quantity shipped : 2606 (86.9%)
  distinct fields across the sample: 25
  fields that could carry how much came back: NONE
```

Be precise about the claim, because the dramatic version is wrong. Somebody
*does* collect the number: under [21 CFR 7.53(b)(4)](https://www.law.cornell.edu/cfr/text/21/7.53)
a recalling firm is *requested* to file recall status reports giving "the number
of products returned or corrected by each consignee contacted and the quantity
of products accounted for." That filing sits with an FDA district office. It is
simply not in any record you or I can read.

And this is a known gap, not my discovery. Reviewing FDA's recall process, GAO
recommended the agency "use the same units of measure to facilitate calculations
of the recovery rate." FDA replied it "does not have the means to currently
implement the recommendation." GAO closed the recommendation **Not Implemented**.

A federal auditor asked for the recovery rate to be computable. The answer was no.

---

## Why this needed Switch, and not a chat channel

Here is the part worth your attention if you are picking a Switch project.

A recall is not one team in one room. It is **several organisations who must not
see each other's books**, and exactly one of them has legal authority the others
do not. Gulf Coast Wholesale must not see Riverside Pharmacy's counts. In a real
recall that is a legal constraint, not a preference.

The usual way to handle that with an LLM is a prompt: *"Do not reveal one
consignee's figures to another."* That is a promise, and promises get argued
with.

Switch's own guidance on shared context says it plainly:

> Membership is the boundary that matters here. [...] Separate rooms preserve
> the boundary.

So I made the structure do the work:

```
recall-skinguard                     ← master room
  @registrar, @regulatory (exclusive), @comms
  the firm's receiving log lives here

recall-skinguard-gulf-coast-wholesale      ← private
  Gulf Coast staff, @liaison-gulf-coast

recall-skinguard-riverside-pharmacy-group  ← private
  Riverside staff, @liaison-riverside
```

**The registrar is a member of neither consignee room.** It cannot be talked
into leaking Riverside's numbers to Gulf Coast, because it has never seen them.
That is not prompt engineering. That is membership.

Take Switch away and this is one channel in which every consignee reads every
competitor's figures — which in a real recall is unlawful. That is my honest
answer to "would the project stop working without Switch?"

The template generates the whole group from the distribution list, so it scales
with the recall rather than with how much YAML I felt like typing:

```yaml
links:
  - from: "recall-{recall}-gulf-coast-wholesale"
    to: "recall-{recall}"
    label: file the account here
```

Note the direction. Which brings me to the first thing that bit me.

---

## Five things about Switch that cost me an afternoon each

This is the section I wish had existed when I started.

### 1. Links are one-way, and a link discloses the target room's *name*

A room's name is visible to everyone in any room that links to it. My first
template linked the master room **to** each consignee room, for convenience.

That quietly published the entire consignee list to every consignee — the exact
disclosure the whole design exists to prevent.

**Rule:** links run consignee → master only. The master never points back. If
your rooms encode a confidentiality boundary, audit your link directions before
anything else.

### 2. The gateway API is **not** on the gateway port

`ports.json` lists four ports, and the obvious reading is wrong:

```json
{ "gateway": 46569, "api": 41019, "mattermost": 39919, "postgres": 42389 }
```

The `gateway` port serves the operator frontend. The gateway **API** is mounted
under `/gateway` on the **api** port. You can check this in one line:

```
http://127.0.0.1:41019/gateway  ->  307     ← the API
http://127.0.0.1:46569/gateway  ->  404     ← not here
```

Admin credentials are in the env file Console generated for its own server:
`~/.config/switchdash/local-switch-server/native/run/switch-core.env`.

### 3. You cannot create managed agents headlessly. Budget for it.

I tried three ways and all three failed, so you don't have to:

- `run_template` from a registered agent fails with **`machine_unresolved`** —
  creating managed agents needs the "can manage agents" capability and a machine.
- The gateway API signs in and provisions rooms and groups fine, but
  `/rooms/from-yaml` **rejects any document carrying an `agents:` block**:
  `Unknown top-level key(s): agents`.
- The hosted-machine routes are for SSH and cloud hosts, not the computer
  Console is running on.

A managed agent is created by Console's own process pulling assignments, not by
a server route. **So the template is run from Console's Templates view, by hand.**
Plan your demo around that; it is not a thing you can CI.

### 4. Deleting a room leaves its Mattermost channel behind

Re-running a template collides with its own leftovers: Switch refuses an agent
name that already exists, and a room deleted in Console leaves the Mattermost
channel. Repeat runs accumulate duplicates, and clearing it by hand is a dozen
clicks every time.

Write the teardown script on day one. Mine is `scripts/console_provision.py
--clean-only`, and I ran it more than anything else in the project.

**Bonus trap:** clicking **Use** twice on a template because the first click
seems slow gives you two complete sets of rooms with identical names, only one
of which is wired up. Ask me how I know.

### 5. A connectionless bot posts with `POST /agents/{id}/message`

Switch has no scheduler and no inbound webhook ([issue #799](https://github.com/sandbox-quantum/switch/issues/799)
is the open request). So an outside event — in my case an FDA record arriving —
reaches a room the only way it can: as a registered agent posting into it.

The catch: agent *operations* need a live MCP session, and a relay bot that just
wants to post has none. `POST /agents/{id}/message` is the connectionless route.
That distinction is not obvious until you have stared at a 400 for a while.

---

## What the registrar actually refuses

Three refusals, each catching something the one before it cannot. This is the
part I would defend in an interview.

**Refusal 1 — it does not add up.** Gulf Coast says: *"We're done, 4,800 bottles
went back, receipt RR-4471, file it as final."* It shipped 7,200. Two thousand
four hundred bottles are unaccounted for, and the sentence was confident while
the arithmetic was not.

Then regulatory affairs — the holder of the `exclusive: true` role — asks the
registrar to close the recall. **It refuses.** Authority is not arithmetic.

**Refusal 2 — it adds up and rests on nothing.** Gulf Coast finds the rest:
1,500 destroyed, 500 quarantined, 400 dispensed. 7,200 of 7,200 exactly. But the
destruction and the quarantine cite no document. A count with no paper behind it
is a sentence, not a fact.

**Refusal 3 — evidenced, and still wrong.** Certificates are attached. Every
count cites a document. The total is exact. And the firm's **own receiving log**
recorded 4,300 bottles arriving back, not 4,800:

```
CLOSURE REFUSED
  - Gulf Coast Wholesale: claims 4800 units returned, but the firm's
    receiving log records 4300 arriving back: 500 units are claimed as
    returned and were never received
```

No amount of self-consistency finds that. It takes the other side of the
transaction.

**And here is where Switch earns its place again:** the liaison never saw that
number. Filing shows a liaison only its own consignee's arithmetic, which
balanced. The receiving log lives in the master room, which Gulf Coast cannot
read — because telling the party being checked what number to agree with is how
you lose the check.

The resolution is worse than the dispute. Those 500 bottles were sold before the
recall notice reached the shop floor, and written up as returns afterwards. They
do not move from *returned* to *found*. They move from recovered to in somebody's
bathroom. Recovery drops to **85.4%**.

That is the number a recall should be closed on. The FDA record has nowhere to
put it.

---

## What it still gets wrong

- **The cross-check covers one bucket of four.** The receiving log is compared
  against claimed *returns*. There is no independent source for destroyed,
  quarantined or dispensed, so the same 500 phantom bottles survive if they are
  relabelled as destroyed with a certificate number.
- **"Cites a document" means a non-empty string.** Nothing fetches
  `destruction-cert/DC-118` to confirm it exists. Refusal 2 establishes that
  somebody was willing to name a document. That is a real step up from a bare
  number, and well short of proof.
- **Flat consignee list, not a distribution tree.** Real recalls fan out through
  distributors to retailers, and that is where recalls actually get lost.
- **The role check is an instruction, not an enforcement.** The registrar reads
  the room's roles and verifies the instructing person holds `regulatory`. The
  *membership* boundary is enforced by Switch whatever the agent does; the role
  check is the agent being told to look. I think it is important to be clear
  about which guarantees are structural and which are behavioural.

---

## Run it yourself

```bash
git clone https://github.com/ANMOLGUPTA-24/closeout.git
cd closeout
./scripts/demo.sh
```

Python 3.10+, standard library only. No network, no API key, no Switch server —
the arithmetic half is deliberately Switch-free so you can check it in thirty
seconds. It exits non-zero if a recall is ever closed when it should not be, so
it doubles as an integration test. 62 tests cover the refusal paths.

The authority model is the other half, and that one genuinely needs Switch:
who may file, who may close, and who is structurally unable to read whose books
are properties of room membership, not of a prompt.

---

If you are starting a Switch project this week: pick a problem where the
*boundary between participants* is the hard part. Switch is not a nicer way to
put an agent in a chat channel. It is a way to make an agent's ignorance
structural — and an agent that cannot see something cannot be talked into
revealing it.

**Repo:** <https://github.com/ANMOLGUPTA-24/closeout> · MIT

*Built for [Flip the Switch](https://www.wemakedevs.org/hackathons/switch).
Built with Claude Code; I directed the design, chose the domain and the room
structure, and can explain any line of it.*
