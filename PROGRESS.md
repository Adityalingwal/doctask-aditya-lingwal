# PROGRESS.md

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-11.** Task 1 scoping is active again. The domain contract is now
**Software Requirements-to-Delivery**, with Client and Software Provider as the
actors; the workflow boundary, primary document types, and core domain cases are
locked in `DECISIONS.md`.

The final deliverable is now locked as a **Requirements-to-Delivery Register**.
The provider-side Delivery Owner is both the system user and human reviewer.
One run is one complete processing cycle for one submitted document batch;
multiple initial and update runs may operate on the same project register.
The human-gate scope is now locked in `DECISIONS.md` — a judgement or a change
to an existing row is gated, a copied fact is not. Next: define the reject
action, what happens once a finding or proposal is rejected.

The pending consistency audit covers the review-screen scope, configurable vs
hardcoded formats, the separate classify stage, citation-preserving extraction,
run idempotency, and the unverified small-register/short-document assumptions.

Added to that audit on 2026-08-11, recorded only — none of these are resolved,
and no product decision changed when they were written down:

- **`request` vs `requirement` drift.** `TASK.md` locks the word `request`, while
  its own opening description, the register lock in `DECISIONS.md`, and the
  information-design checklist below all say `requirement`. Nothing records
  whether this is an intended rename or a slip.
- **The locked vocabulary has no canonical home.** `TASK.md` states the project's
  words are fixed in `DECISIONS.md`, but `DECISIONS.md` has no vocabulary section.
- **`pile` vs `batch` drift.** `pile` sits in the locked vocabulary, the run lock
  says a run consumes one submitted document batch, and `sample-piles/README.md`
  still says a pile is what a single run consumes.
- **Deliverable-side rule D2 depends on an unlocked status.** D2 forbids a
  `Delivered` row without a testing outcome, but the status values it names live
  in the register section marked NOT LOCKED.
- **Stale coverage index in the working notes.** It still states Task 1 scoping is
  complete as of 2026-08-09 and that the next phase is architecture.
- **Status mismatch across the two files.** Request identity, request granularity,
  the rules playbook with its finding shape, and the review-screen scope are
  labelled LOCKED or `v1 starting point` in `DECISIONS.md`, while the matching
  items in the roadmap below are still open. Which label is authoritative is
  undecided.
- **Review-screen mockup implies per-row approval.** The review-screen scope
  section in `DECISIONS.md` shows `[✓] [✗]` against the register in its
  mockup, implying per-row approval, which the human-gate scope locked on
  2026-08-11 does not require for plain rows.

`TASK.md` is written apart from its Commands section, which stays empty until
the project structure exists.

**LangGraph learning exercise complete.** A throwaway five-node graph with
SQLite checkpointer, interrupt/Command, and kill-and-resume was built and tested
externally. The six core concepts (State, Node, Edge, Conditional Edge,
Checkpointer, interrupt/Command) are in hand.

**Ingest pipeline scoping started.** PDF library choice locked: `pdfplumber` for
extraction, `pypdf` for encryption detection. Decision and evidence in
`DECISIONS.md`. Accepted formats declared in `README.md`.

No code yet in this repository.

Documentation history now follows an explicit policy: the Decision Log is
append-only, canonical sections contain only current truth, and current-facing
files do not carry stale alternatives. Root `CLAUDE.md` imports the repository
working contract and defines source priority and continuation rules for future
Claude Code sessions.

## Planning roadmap

This section tracks only status and continuation order. Decision reasoning stays
in `DECISIONS.md`; implementation detail belongs in code and tests.

### 1. Product contract

- [ ] Define the brief acceptance contract with exact pass/fail checks.
- [x] Lock domain, actors, workflow boundary, and document types.
- [x] Select the Requirements-to-Delivery Register.
- [x] Choose the actual system user and human reviewer.
- [x] Define one-run scope.
- [x] Define the human-gate scope.
- [ ] Define the incremental input contract.
- [ ] Decide coverage or defended cuts for behaviours 6–10.
- [ ] Lock the React, FastAPI, and MCP boundary.

### 2. Information design

- [ ] Define the core domain terms and relationships.
- [ ] Define requirement identity and granularity.
- [ ] Define register fields and statuses.
- [ ] Define evidence and citation requirements by file format.
- [ ] Define rules, findings, and no-findings behaviour.
- [ ] Define export, audit-history, and unchanged-proof contracts.

### 3. System architecture

- [ ] Map components and end-to-end data flow.
- [ ] Define document parsing and model/provider boundaries.
- [ ] Define run identity, idempotency, and concurrency behaviour.
- [ ] Define LangGraph state, nodes, edges, and checkpoints.
- [ ] Define database tables, migrations, versions, and audit trail.
- [ ] Define the human-review state machine.
- [ ] Define watched-folder and focused-update architecture.
- [ ] Define prompt-injection, no-bluff, and security controls.
- [ ] Define FastAPI, MCP, and React contracts.
- [ ] Define failure, retry, logging, timing, and cost behaviour.

### 4. Proof and implementation plan

- [ ] Build the requirement-to-acceptance traceability matrix.
- [ ] Design synthetic piles and the edge-case matrix.
- [ ] Define the no-live-key automated test strategy.
- [ ] Plan implementation slices and repository boilerplate.
- [ ] Plan fresh-clone verification and demo evidence capture.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in request matching; the whole register fits in one model call, so nothing needs narrowing | Reopened 2026-08-11 — depends on choosing a register and measuring real sample piles |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, client requirements documents, and testing feedback are expected to be short, so vector retrieval may not be needed | Open — if real documents turn out large, pgvector retrieval comes back in |

## Blockers

_None open._

## Log

Newest first.

**2026-08-11 — Human-gate scope locked**
Locked the 13-scenario human-gate checklist in `DECISIONS.md`: gated wherever
the system judges or changes an existing row, not where it only copies a fact.
Ticked the product-contract checklist item and queued one more
consistency-audit entry — the review-screen mockup's per-row `[✓] [✗]`.

**2026-08-11 — Consistency audit widened (housekeeping only)**
Recorded six further unresolved issues found during a read-only context audit:
four terminology or dependency drifts, one stale coverage index, and the mismatch
where several 2026-08-09 decisions read as locked in `DECISIONS.md` while their
information-design counterparts here are still open. Nothing was resolved and no
product decision changed. Also corrected the project auto-memory, which still
claimed scoping was complete and carried the superseded domain and run-scope
wording.

**2026-08-11 — Documentation handoff hardened**
Added an append-only decision-history policy, restored superseded decisions,
removed the conflicting old run-scope section, and added root Claude Code
continuation instructions. Added permanent cross-agent rules for verifying
memory, separating fact from inference, and asking when material evidence is
missing. No product behaviour changed in this cleanup.

**2026-08-11 — Domain corrected; register selected**
Replaced the previous software-feature-delivery framing with the agreed
Software Requirements-to-Delivery contract across `README.md`, `TASK.md`, and
`DECISIONS.md`. Selected the Requirements-to-Delivery Register after comparing
it with a brief and report; queued six consistency issues for their relevant
decision blocks before architecture begins. Added the four-phase planning
roadmap so another agent can continue from the exact next decision. Locked one
provider-side Delivery Owner as both system user and human reviewer for V1.
Separated the continuing project register from individual initial and update
runs, and locked one run as one complete document-batch processing cycle.

**2026-08-09 — Task 1 scoping complete, `TASK.md` written**
Worked through the orchestration choice and the full domain scoping in one
pass. Rejected alternatives are recorded in `DECISIONS.md` so they do not
resurface. Wrote `TASK.md`: what this is, where the truth lives, code
conventions, a never-do list split into "the system must never" and "you must
never", a definition of done, and the git rule (branch commits and pull requests
allowed, merging is not).

**2026-08-09 — LangGraph learning exercise completed**
Built a throwaway five-node graph with SQLite checkpointer, interrupt/Command,
and kill-and-resume outside this repository. Verified all three scenarios:
(a) interrupt → approve/reject with conditional routing, (b) kill during
interrupt → resume with same thread_id skips already-completed nodes, (c) two
thread_ids keep state separate. The six concepts are in hand for graph design.

**2026-08-09 — PDF library choice locked, README updated**
Tested pdfplumber, pypdf, and pdfminer.six across 7 PDFs (59-page IRS doc with
14 tables, 22-page MSA, encrypted/scanned synthetic). Chose `pdfplumber` for
extraction + `pypdf` for encryption detection. Updated `DECISIONS.md`
(table entry + detailed section), `README.md` (formats table + limitations), and
`PROGRESS.md` (this entry).
