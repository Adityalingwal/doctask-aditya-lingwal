# PROGRESS.md

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-12.** Phase 1 (product contract) and Phase 2 (information design)
are complete. The final deliverable remains the seven-column
**Requirements-to-Delivery Register**, with per-cell citations, six status
values, and the provider-side Delivery Owner as both system user and human
reviewer.

Phase 3 (system architecture) is closed apart from two remainders that belong
to later build slices: the rules and findings tables, and the MCP tool surface
plus React screen shape. The seven slice-1 database tables, migrations from the
first table, five slice-1 API endpoints, pipeline, LangGraph state and
checkpoints, review state machine, watched-folder trigger, focused-update
contract, prompt-injection boundary, failure handling, retry, logging, timing,
and estimated cost behaviour are locked in `DECISIONS.md`.

Runs use random UUIDs, a durable per-project database lock, and one waiting
run. The project folder is polled every 10 seconds and starts a run after 30
seconds of quiet when new or changed files are waiting and no run is active.
Extract has one retry and a 120-second per-call timeout; the narrow
answer-to-checkpoint kill window is documented as a one-call repeat
limitation. Logs are JSON lines on stdout, stage timing is measured, and run
cost is reported as an estimate from token counts in model response metadata
and a configured rate.

Phase 4 proof and implementation planning is next. The short-document/pgvector
assumption remains open until real sample projects are measured. `TASK.md` is
written apart from its Commands section, which stays empty until the project
structure exists. No code exists in this repository yet.

## Planning roadmap

This section tracks only status and continuation order. Decision reasoning stays
in `DECISIONS.md`; implementation detail belongs in code and tests.

**These four are not four gates in a row.** Phases 1 and 2 are closed. Phase 3
is closed except for the database and interface remainders explicitly kept
with their later slices below. Phase 4's items are per-slice, not a gate before
implementation.

### 1. Product contract

- [ ] Define the brief acceptance contract with exact pass/fail checks.
      Deferred to build time — decision recorded in `DECISIONS.md`.
- [x] Lock domain, actors, workflow boundary, and document types.
- [x] Select the Requirements-to-Delivery Register.
- [x] Choose the actual system user and human reviewer.
- [x] Define one-run scope.
- [x] Define the human-gate scope.
- [x] Define the incremental input contract.
- [x] Decide coverage or defended cuts for behaviours 6–10. Nothing is cut;
      each behaviour is assigned to a slice in `DECISIONS.md`'s build order.
- [ ] Lock the React, FastAPI, and MCP boundary. Deferred to build time —
      decision recorded in `DECISIONS.md`.

### 2. Information design

- [x] Define the core domain terms and relationships.
- [x] Define requirement identity and granularity.
- [x] Define register fields and statuses.
- [x] Define evidence and citation requirements by file format.
- [x] Define rules, findings, and no-findings behaviour.
- [x] Define export, audit-history, and unchanged-proof contracts.

### 3. System architecture

- [x] Map components and end-to-end data flow.
- [x] Define document parsing and model/provider boundaries.
- [x] Define run identity, idempotency, and concurrency behaviour.
- [x] Define LangGraph state, nodes, edges, and checkpoints.
- [ ] Define database tables, migrations, versions, and audit trail. The
      slice-1 tables are settled; the rules and findings tables arrive with
      the rules-engine slice.
- [x] Define the human-review state machine.
- [x] Define watched-folder and focused-update architecture.
- [x] Define prompt-injection, no-bluff, and security controls.
- [ ] Define FastAPI, MCP, and React contracts. The five slice-1 endpoints are
      settled; the MCP tool surface and React screen shape arrive with their
      slices.
- [x] Define failure, retry, logging, timing, and cost behaviour.

### 4. Proof and implementation plan

- [ ] Build the requirement-to-acceptance traceability matrix.
- [ ] Design synthetic projects and the edge-case matrix.
- [ ] Define the no-live-key automated test strategy.
- [ ] Plan implementation slices and repository boilerplate.
- [ ] Plan fresh-clone verification and demo evidence capture.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in requirement matching; the whole register fits in one model call, so nothing needs narrowing | Register now chosen — seven columns, `DECISIONS.md` "Register shape", 2026-08-11 — still open until measured against real sample projects |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, client requirements documents, and testing feedback are expected to be short, so vector retrieval may not be needed | Open — if real documents turn out large, pgvector retrieval comes back in |
| 2026-08-11 | Source documents run 5–10 pages (40–50 would already be unusual) | The domain is small teams and freelancers | A config page-limit plus a stated README limitation cover documents beyond it — chunking was therefore not built |

## Blockers

_None open._

## Log

Newest first.

**2026-08-12 — Remaining Phase 3 architecture locked**
Closed the idempotency decision with its one-call repeat limitation, plus
watched-folder triggering, prompt-injection controls, failure and retry
behaviour, and logging, timing, and estimated cost reporting.
Runs now auto-start after a 10-second poll and 30-second quiet period; model
calls use two attempts and a 120-second per-call timeout. Phase 3 now retains
only the stated later-slice remainders for rules/findings tables and the
MCP/React contracts. Added the three current README limitations for a repeated
Extract call, files waiting during Review, and estimated rather than billed
cost.

**2026-08-12 — All 27 review findings resolved; three Phase 3 locks recorded**
Applied the agreed fix for every finding from the two documentation reviews
and removed the "Review findings — open" section, which is now empty. Seven
Decision Log rows were marked superseded and eleven new dated rows added,
covering: a sixth status value (`No evidence yet`) held in code rather than
config, the narrowed citation-location claim, the dropped intra-file delta
promise, rules-change re-runs, `POST /runs` taking a `project_id`,
in-process execution with a durable database lock and startup resume, the
`closed without export` terminal status with proposed rows and changeable
review decisions, no behaviour cut, and the three Phase 3 locks (OpenRouter
with `config/model.yaml`, one injected model client, and `finish-review`
refused while any gated decision is missing). Ticked the behaviours 6–10
coverage item and Phase 3's parsing and model/provider boundary. `README.md`
gained the rules default, the model-access requirement, the full-re-read
limitation, and a declared-set format table that no longer reads as shipped
capability; `TASK.md`'s review-UI line now points at the locked design;
`config/README.md` gained `model.yaml` and the page limit.

**2026-08-11 — Two independent documentation reviews run; 27 findings recorded**
Two models, Fable and Codex, reviewed the repository documentation separately
against the same brief, with no sight of each other's work. Their findings are
merged into "Review findings — open" above: 6 blocking slice 1, 10 to fix
before submission, 9 minor, and 2 coverage gaps. Five were raised by both
reviewers independently. Nothing has been judged or fixed yet; each is decided
one at a time, and its entry is removed once its fix lands.

**2026-08-11 — Phase 3 architecture: pipeline, state, run identity, database tables, and API locked**
Locked in `DECISIONS.md`: the six pipeline stages (Ingest through Commit)
with where the model is called, Extract's one-document-per-call shape with
its citation/fabrication-detector mechanism, Match and Examine kept
separate, LangGraph state-vs-database and checkpoint placement, run
identity's slice-1 share (UUID, per-project lock, one queued waiting run),
the seven slice-1 database tables, and the five slice-1 API endpoints.
Deliberately partial — five Phase 3 points remain untouched. Rewrote the
stale closing line in "One-run scope" to point at the new run-identity
section. Added three README limitations (R3 timing, one-run-per-project
queueing, the document size limit).

**2026-08-11 — Vocabulary locked; consistency-audit backlog cleared**
Renamed `request` → `requirement` and `pile` → `project` throughout
`DECISIONS.md`, `TASK.md`, and `PROGRESS.md` (`batch` was already its own
word and stays untouched); Decision Log rows, `documentation/`, and the
frozen review-screen mockup keep the old words on purpose. Added
`DECISIONS.md`'s `## Vocabulary` section, the canonical home `TASK.md`
pointed at but that never existed, and fixed the pointer. Renamed
`sample-piles/` to `sample-projects/` (plain `mv`, no git
history) and rewrote its README, which had called a project's whole folder
"what a single run consumes" — that is a batch. Resolved and removed six
audit items: citation-preserving extraction, the classify-stage remnant,
`request`/`requirement` drift, the vocabulary-home gap, `pile`/`batch` drift,
and the status-label mismatch; the short-document/pgvector assumption stays
open. Superseded the 2026-08-09 "deliberately hardcoded" accepted-format-list
row: the list now lives in `config/formats.yaml`, the readers stay in
`app/ingest/`, and a startup check reconciles the two — new Decision Log row
added. Banner-marked the review-interface mockup as superseded (stale
`classify` stage, `Delivered` status, per-row `[✓][✗]`); the redesign itself
stays deferred to the architecture phase, not done now. Corrected the
working-notes coverage-index date. Added the reject-suppression limitation
and the run-trigger assumption to `README.md`, and a rule to `TASK.md` on
what actually earns a `DECISIONS.md` entry.

**2026-08-11 — Phase 1 and Phase 2 closed**
Locked the remaining decisions in `DECISIONS.md`: human-gate actions
(Approve/Reject, reject kept permanently in the run record), the incremental
input contract (batch = every new and changed file waiting when a run
starts), the seven-column register shape with per-cell citations and five
status values, citation format per file type, and export/audit-history/
unchanged-proof. Ticked the incremental-input-contract item and all six
Phase 2 items; the three remaining Phase 1 items are logged as deferred to
build time, not cut. D2 now reads `Done`, which resolves and removes the
"D2 depends on an unlocked status" audit bullet above. Added three working
rules to `TASK.md`.

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
