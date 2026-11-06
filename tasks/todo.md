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

## Phase 0 — GO/NO-GO (target 2h)  [IN PROGRESS]
- [x] Preflight: Ubuntu 24.04, x86_64, native Linux (not WSL -> dodges #1500),
      gnome-keyring running, Wayland session (may need --ozone-platform=x11).
- [x] Console v0.40.1 amd64 .deb downloaded to vendor-dl/ (254MB).
- [ ] **BLOCKED on user:** `sudo apt-get install -y ./vendor-dl/switch-console-amd64.deb`
      (sudo cannot prompt from the agent shell). Fallbacks ready:
      `--ozone-platform=x11 --disable-gpu`, `--password-store=gnome-libsecret`,
      `pkill -x switch-console`.
- [x] Confirm user is in `docker` group + compose plugin present (both OK).
- [ ] Local server + bundled Mattermost up (Docker required for Mattermost).
- [ ] One agent (Claude Code) answering in one room.
- [ ] Set Callback Base Url, else approval buttons degrade to typing a number.
- **NO-GO fallback:** Docker-only `just standalone-up` (API 8000 / gateway 3000 / MM 8065),
      agents via raw protocol. If both fail -> STOP and re-plan with user.

## Phase 1 — Structure (target +4h)  [MOSTLY DONE, needs a live server to verify]
- [x] `closeout.template.yaml`: group of 3 rooms (master + westside + midtown),
      `links:` inward only (a link discloses the target room's name to everyone
      in the linking room, so master never points back at consignees).
- [x] Exclusive role `@regulatory` + shared `@comms`; room `docs:` carries the
      closure rule. Registrar is a member of the master room ONLY -> it
      structurally cannot read consignee rooms. Switch's own words:
      "Membership is the boundary that matters here."
- [ ] Verify the template actually provisions (needs Console). `POST /rooms/from-yaml`
      takes the same shape, which gives judges a second reproduction path.
- [ ] Relay bot agent registered; posts the openFDA recall into the master room
      via `POST /agents/{id}/message` (Switch has no scheduler/inbound webhook).

## Phase 2 — Reconciliation engine (target +6h)  [DONE]
- [x] Deterministic reconciliation: shipped vs returned/destroyed/quarantined/dispensed.
- [x] Contradiction detection: false_completion, overage, duplicate_report.
- [x] Silence != completion: a consignee with a shipment and no filing still counts.
- [x] `recovered` (returned+destroyed) kept distinct from `accounted` — the GAO point.
- [x] 19 pytest tests, all passing, incl. every refusal path + bool-as-count guard.

## Phase 3 — The two-run demo (target +6h)  [DONE offline; needs re-staging in rooms]
- [x] Built on the REAL FDA record F-0616-2018 (Class I Listeria, Nyblad
      Orchards, "5278 units shipped", status Terminated, no recovery rate stated).
- [x] **Run A:** account balances -> 90.5% recovery -> closure authorized, and
      500 units are explicitly signed for as never recovered.
- [x] **Run B (THE POINT, never cut):** Westside returns 2878/4278 and asserts
      completion -> refused as a contradiction; then `close` by `@regulatory`
      is ALSO refused. Authority is not arithmetic.
- [x] `scripts/demo.sh` runs offline, no network/key/server, exits non-zero on
      a wrong outcome so it doubles as an integration test.
- [ ] Re-stage both runs as actual room conversations once Console is up.

## Phase 4 — Submission (Sat)  [ ]
- [ ] README: problem first, mermaid diagram, "How Switch is used" depth table,
      working quickstart, test command, **Honest limits**, **AI disclosure**.
- [ ] 2-3 min demo video, user narrates. Run B must be on screen.
- [ ] Public repo, MIT. Submit by 21:00 IST.
- [ ] Stretch only if ahead: blog post (Best Blog side track).

## Review
(to be filled in after build)
