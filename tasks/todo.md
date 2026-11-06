# Closeout — Flip the Switch (Track 01, Best Business Workflow)

**Deadline: Sat 7 Nov 2026, 23:59 IST.** Target submit: 21:00 IST (3h buffer).
Judging: Use of Switch 30% / Technical execution 25% / Creativity & impact 25% / Presentation 20%.

## Thesis
A product recall can only be closed by **reconciliation**, never by assertion.
The agent is a registrar: it holds the recall open and refuses closure until
units shipped == returned + destroyed + accounted-unrecoverable.
Humans assert; the agent reconciles and declines.

Evidence: only ~36% of recalled food is ever recovered (GAO-05-51); FDA verification
averaged 31 days; HHS OIG found 57 days average to even start a recall.

## Why Switch is load-bearing (the 30%)
- **Exclusive roles** — only `@regulatory` can authorize closure; Switch records who answered.
- **Linked rooms** — one room per consignee, linked to a master recall room. You legally
  cannot show Pharmacy A the data of Pharmacy B. A single channel cannot express this.
- **Relay bot** — openFDA enforcement API (CC0) -> `POST /agents/{id}/message`.
  Fills Switch's documented no-scheduler / no-inbound-webhook gap.
- **Approval cards** with custom options for the closure gate.
- **Template YAML** — judge runs one command, whole multi-room/multi-role structure appears.

## Hard constraints
- All reconciliation numbers computed in plain code. **Never LLM-estimated.**
- Synthetic lot->consignee data only. Real recall *records* from openFDA; no real customer data.
- Offline/reset mode so a judge reproduces without any API key.
- No AI attribution in commit messages.

## Phase 0 — GO/NO-GO (target 2h)  [ ] 
- [ ] Install Console .deb (x86_64). Fallbacks ready: `--ozone-platform=x11 --disable-gpu`,
      `--password-store=gnome-libsecret`, `pkill -x switch-console`.
- [ ] Confirm user is in `docker` group + compose plugin present.
- [ ] Local server + bundled Mattermost up (Docker required for Mattermost).
- [ ] One agent (Claude Code) answering in one room.
- [ ] Set Callback Base Url, else approval buttons degrade to typing a number.
- **NO-GO fallback:** Docker-only `just standalone-up` (API 8000 / gateway 3000 / MM 8065),
      agents via raw protocol. If both fail -> STOP and re-plan with user.

## Phase 1 — Structure (target +4h)  [ ]
- [ ] `closeout.template.yaml`: master recall room + 2 consignee rooms, linked.
- [ ] Exclusive roles: `@regulatory`, `@distributor`, `@pharmacy-lead`, `@comms`.
- [ ] Addressing rules so only `@regulatory` can approve closure.
- [ ] Relay bot agent registered; posts an openFDA recall into the master room.

## Phase 2 — Reconciliation engine (target +6h)  [ ]
- [ ] Lot -> consignee distribution tree (synthetic).
- [ ] Deterministic reconciliation: shipped vs accounted; unaccounted delta.
- [ ] Contradiction detection (consignee says "all returned", quantities disagree).
- [ ] pytest suite over the arithmetic + the refusal path.

## Phase 3 — The two-run demo (target +6h)  [ ]
- [ ] **Run A:** reconciles -> closure proposed -> `@regulatory` approves -> closed.
- [ ] **Run B (THE POINT, never cut):** 1,400 units unaccounted -> human says "we're done"
      -> agent **refuses** and names what's missing.

## Phase 4 — Submission (Sat)  [ ]
- [ ] README: problem first, mermaid diagram, "How Switch is used" depth table,
      working quickstart, test command, **Honest limits**, **AI disclosure**.
- [ ] 2-3 min demo video, user narrates. Run B must be on screen.
- [ ] Public repo, MIT. Submit by 21:00 IST.
- [ ] Stretch only if ahead: blog post (Best Blog side track).

## Review
(to be filled in after build)
