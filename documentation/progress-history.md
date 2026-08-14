# Progress history

This is the detailed pre-compaction progress record frozen from `PROGRESS.md`
at commit `2e14c91` on 2026-08-13. Completed dated narrative and resolved
blockers belong here. Current status, active blockers, assumptions and next
actions live in root `PROGRESS.md`; the exact byte-for-byte source is
`documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`.

New completed entries are added newest-first below this header.

**2026-08-14.** Built `runs.finished_stages`, removed timing and cost from the
application in full, and built `GET /runs` plus its MCP tool `list_runs`, on
`finished-stages-and-list-runs`, cut from `main` at `d4c9eab`. Written before
any implementation: the brief's six Python and two front-end never-do tests,
run at that baseline. Five of the six Python tests share one file and failed
together on the whole `app.runs.finished_stages` module not existing; the
sixth failed because `GET /runs` answered `405` and `list_runs` was an unknown
tool. Of the front end's cases, five passed as regression guards and four
failed, one of them reproducing the literal "1 Jan" bug `new Date(null)`
causes for a run with no `started_at`. Built: migration `20260814_0010`, which
drops `stage_timings`, `token_usage`, `estimated_cost_usd` and
`cost_unknown_reason` and adds `runs.finished_stages`, a jsonb object keyed by
stage name and written with the same `||` merge the dropped column used, so a
re-entered node overwrites its own key; `app/runs/finished_stages.py`, which
replaces the deleted `app/runs/cost_and_timing.py` with one function that
records a stage's mark and one that reads it back as an ordered list of stage
names; Review's finished mark moved to the second of its two call sites in
`app/graph/register_graph.py`, after `review_finished_at` is set, so a run
still waiting for the Delivery Owner is never reported finished; the whole
token-usage chain removed — `ReportedUsage`/`ModelAnswer` out of
`call_the_model.py`, `CostRates`/`read_cost_rates` out of `client.py`, and the
three model-boundary functions (`read_one_document`, `match_requirements`,
`examine_register`) now return just their answer; and `app/runs/list_runs.py`,
one core function both `GET /runs` and `list_runs` call, returning
`{"runs": [...]}`, newest first, no cap, `started_at` sent as `null` rather
than substituted with `created_at`. On the screen: `Stages.jsx`'s precedence
fixed so the run's own stage wins over a reported "done" only while the run is
active, and `RunList.jsx` gets an explicit `started_at === null` check ahead of
`new Date(...)`. `tests/runs/test_timing_and_cost.py` and one column-reading
test in `test_schema.py` were deleted outright, and two pre-existing tests
that hardcoded a stale six-tool MCP count were found by a repository grep and
updated to seven. Proof: 129 Python tests and 20 front-end tests passed, no
live API key.

**The timing-and-cost verification this replaces**, kept here as the historical
record now that the behaviour itself is gone: two documents through export —
ingest 0.005s, extract 0.005s, match 0.006s, examine 0.003s, review 0.206s,
commit 0.011s, total 0.236s; 4 calls reported 4,400 prompt and 570 completion
tokens, estimated 0.002672 USD (Intake portal, `operations-timing-cost`
branch, 2026-08-14). Three documents (`.md`, `.docx`, `.pdf`) through export —
ingest 0.029s, extract 0.011s, match 0.008s, examine 0.004s, review 0.152s,
commit 0.013s, total 0.217s; 5 calls reported 5,600 prompt and 750 completion
tokens, estimated 0.003440 USD (Northside Dental, same branch and date). A run
killed inside Extract with the third document's call in flight, resumed, asked
about that document twice and still reported one `extract` entry, 5 calls
reporting usage and 550 prompt tokens, not 650 (Kill and resume, not doubled,
same branch and date). All three used the scripted client, so every figure was
arithmetic over fixture tokens, never a measured provider charge.

**2026-08-14.** Built the reliability slice on `reliability-proof`, cut from
`main` at `bb24476`. Written before anything else: the five never-do tests, run
at that baseline. All five passed there, so this slice added no production code
and changed none — the lock, the queue and the Extract path were already right
and are now proven. Built: `tests/test_two_projects_at_once.py`, which runs two
projects over one database and shows them live together twice over, by a polled
status and by two model calls started inside the scripted call delay, then
checks that no row, citation, decision, finding or log line of one appears in
the other; `tests/test_same_project_queue.py`, which holds one waiting run
across four requests, proves that run's batch is formed when it starts rather
than when it was queued, and picks it up after a `done` run and after a
`failed` one; and `tests/test_document_instruction_is_reported.py`, which
drives `meeting-notes-20-mar.md` and its buried line through a real run and
finds it stored and logged as an embedded instruction, with no row, no cell, no
gated proposal and no export carrying it. The test harness gained a run-event
log the application can be started with, model-call timestamps, and readers for
a run's findings and a document's stored extraction. A negative control,
written and then deleted, confirmed the overlap check reports no overlap when
the same two projects run one after the other. Two limitations were found and
recorded rather than fixed: a reported instruction has no surface a person
reads, and run events below `WARNING` reach nothing under the shipped uvicorn
logging configuration. Proof: 122 passed, no live API key; the three new files
five times in a row, five passes.

**2026-08-14.** Built the incremental update slice on `incremental-update`,
cut from `main` at `4132a2e`. Written before its code: the seven never-do
tests, run at that baseline. Three of them failed there and now pass — the
watcher started nothing, no withdrawal was ever raised, and a rules-only run
ended without changes instead of examining. The other four passed at the
baseline and stay as regression guards: unaffected rows already came back
byte-identical, an unchanged file was already never re-read, nothing deleted a
row, and the export gate already held. Built: `config/watcher.yaml` and
`app/runs/watch_source_folders.py`, which start a run through the same
`start_or_queue_run` the endpoint uses; the rules-only route, from Ingest
straight to Examine when the frozen rules differ from the ones the register was
last judged against; and requirement withdrawal end to end — migration
`20260814_0007`, `app/register/withdraw_rows.py`, the fourth review-queue kind,
and the first absence citation this system has written. Extract now routes on
to Match when the batch read a document a committed row came from, even with no
requirement found, and Match makes no model call when there is nothing to
match. Proof: 116 passed, no live API key; both corpora driven through a first
and a second run with the unaffected rows compared as stored.

**2026-08-13.** Built the two decisions locked earlier the same day and
deliberately left unbuilt: the `review_finished_at` replay guard and the
loopback-only network bind. Migration `20260813_0004` adds
`runs.review_finished_at`; `claim_review_finished` sets it in the same
statement that takes a run out of review; the Review node and `submit_decision`
both gate on it, so a crash-and-restart resume can no longer replay the
pre-interrupt work and reopen a finished review. The Dockerfile's `uvicorn` now
reads `APP_HOST`, defaulting to `127.0.0.1`, via an exec'd shell command so
`SIGKILL` still reaches `uvicorn` as PID 1; Compose sets `APP_HOST=0.0.0.0` for
the app service and publishes `127.0.0.1:8000:8000`, matching `db`. Proof:
`test_finished_review_does_not_reopen_on_resume` and
`test_decision_refused_after_review_finished_even_if_status_regresses` in
`tests/test_finish_review.py`; `tests/test_loopback_bind.py`. Full suite: 55
passed, no live API key.

---

# PROGRESS.md (historical source)

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-13.** Slice 1 is complete and merged into `main` — slice 1a, slice
1b, and the eight fixes from a two-reviewer round. 51 tests, all runnable with
no live API key. No live model has ever been called from this repository;
every run and every test used the scripted client.

Phase 1 and Phase 3 are closed. Phase 1's two deferred items — the brief
acceptance contract and the React/FastAPI/MCP boundary — and Phase 3's two
remainders — the database tables and the FastAPI/MCP/React contracts — are
locked in `DECISIONS.md`. Phase 4 is what remains, plus the seven build slices
after slice 1.

Slice 1's proven scope: the Ingest-to-Commit graph for `.md` documents, the
six API endpoints, project creation by `POST /projects` and startup seeding,
the review queue, kill-and-resume from a real `SIGKILL`, the two new terminal
run statuses, configuration-vs-transient failure classification, and the
durable project lock with its waiting-run queue. The lock and queue are built
but not yet proven — their tests arrive with the concurrency slice. Built is
not proven.

The demo corpus's first document exists
(`sample-projects/intake-portal/meeting-notes-10-mar.md`); the other three demo
documents and all six second-run documents are designed but not written. The
edge-case matrix, traceability matrix, and fresh-clone verification remain
open. `TASK.md`'s Commands section stays empty until its commands have
actually been verified from a fresh clone.

## Planning roadmap

This section tracks only status and continuation order. Decision reasoning stays
in `DECISIONS.md`; implementation detail belongs in code and tests.

**These four are not four gates in a row.** Phases 1, 2 and 3 are closed.
Phase 4's items are per-slice, not a gate before implementation.

### 1. Product contract

- [x] Define the brief acceptance contract with exact pass/fail checks.
      Locked in `DECISIONS.md` "Brief acceptance contract".
- [x] Lock domain, actors, workflow boundary, and document types.
- [x] Select the Requirements-to-Delivery Register.
- [x] Choose the actual system user and human reviewer.
- [x] Define one-run scope.
- [x] Define the human-gate scope.
- [x] Define the incremental input contract.
- [x] Decide coverage or defended cuts for behaviours 6–10. Nothing is cut;
      each behaviour is assigned to a slice in `DECISIONS.md`'s build order.
- [x] Lock the React, FastAPI, and MCP boundary. Locked in `DECISIONS.md`
      "MCP server — tool surface", "MCP server — placement and validation",
      and "Review interface — scope".

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
- [x] Define database tables, migrations, versions, and audit trail. The
      slice-1 tables and the findings table design are locked; the findings
      table itself arrives with the rules-engine slice.
- [x] Define the human-review state machine.
- [x] Define watched-folder and focused-update architecture.
- [x] Define prompt-injection, no-bluff, and security controls.
- [x] Define FastAPI, MCP, and React contracts. The six endpoints, the MCP
      tool surface and placement, and the five-section review screen are
      locked in `DECISIONS.md`.
- [x] Define failure, retry, logging, timing, and cost behaviour.

### 4. Proof and implementation plan

- [ ] Build the requirement-to-acceptance traceability matrix.
- [ ] Design synthetic projects and the edge-case matrix. The demo project and
      the second-run project are designed; the edge-case matrix remains open.
- [ ] Define the no-live-key automated test strategy. Slice 1 is settled;
      later slices add their own tests.
- [x] Plan implementation slices and repository boilerplate.
- [ ] Plan fresh-clone verification and demo evidence capture. One demo step is
      already chosen: raise R3's `max_days` from 14 to 30 in `config/rules.yaml`,
      re-run, and show the R3 finding disappear — configuration over code proved
      on screen rather than asserted.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in requirement matching; the whole register fits in one model call, so nothing needs narrowing | Register now chosen — seven columns, `DECISIONS.md` "Register shape", 2026-08-11 — still open until measured against real sample projects |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, client requirements documents, and testing feedback are expected to be short, so vector retrieval may not be needed | Open — if real documents turn out large, pgvector retrieval comes back in |
| 2026-08-11 | Source documents run 5–10 pages (40–50 would already be unusual) | The domain is small teams and freelancers | A config page-limit plus a stated README limitation cover documents beyond it — chunking was therefore not built |
| 2026-08-12 | The model client's configuration-failure classification is correct for real SDK exceptions | The classifier reads `status_code` off the SDK's typed exceptions; only the 401 path is driven by a test, and 402/403/404 share the same dictionary lookup | Open — no live model call has ever been made, so no real SDK exception has been seen |
| 2026-08-12 | The two-attempt retry policy matches the OpenAI SDK's own behaviour closely enough | The SDK's own policy (retries on 408/409/429/5xx, no retry on 400/401/402/404, exponential backoff) is used; the locked 5-second fixed wait is not hand-implemented | Open — matches the locked table's shape but not its exact wait |
| 2026-08-12 | The concurrency mechanism works as designed | The durable lock is exercised only indirectly through kill-and-resume; the waiting-run queue and two-projects-side-by-side have no test at all | Open — built is not proven; tests arrive with the concurrency slice |

## Blockers

- **The audit table cannot represent an attachment event.** `ck_audit_cell_name`
  plus a `NOT NULL cell_name` on `audit` means an entry like "finding F-02
  attached to row 5" cannot be written at all — and `DECISIONS.md`'s audit
  section explicitly says attachments arriving or leaving are recorded there.
  Found by Fable in the slice 1a review (its N2) and deliberately not fixed
  then, because nothing that could hit it existed yet. That is still true —
  slice 1b has no findings. Must be named in the rules-and-findings slice's
  brief before that slice starts.

- **The document-type buckets are not enforced anywhere.** `DECISIONS.md`
  locks primary / related additional / unrelated, and Extract is asked for one
  of five values, but only `unrelated` changes behaviour; a model returning an
  unexpected type is accepted and treated as related. Open since the slice 1b
  implementation report raised it.

- **The broad worktree bind mount stays for local development, on purpose.**
  `docker-compose.yml` mounts `.` at `/workspace`, so the git-ignored `.env`
  is readable inside the container and local files override what is baked into
  the image. Accepted deliberately so local iteration stays fast. Before final
  whole-project verification the mount must be removed or narrowed and the
  verification rerun against the image alone. The development PostgreSQL
  volume also holds stale pre-review data and should be wiped once so the demo
  starts from a genuinely empty database.

## Log

Newest first.

**2026-08-13 — Slice 1b built, reviewed, and fixed; handoff transcribed**
Slice 1b landed in pull request #2 (merged into `main`): the Ingest-to-Commit
graph, the six API endpoints with project creation, the review queue, the
durable lock and waiting-run queue, and the kill-and-resume test over a real
`SIGKILL`. Two independent reviewers then raised six distinct findings (F1–F5
plus Codex 2). Eight decided fixes landed on top: the merged-proposal marker
(F1), the Match coverage check (Codex 2), the `failed` and
`ended without changes` terminal statuses, configuration-vs-transient failure
classification (F3), the read-and-exported change-detection conditions with
their same-day correction (F5), the atomic `finish-review` claim (F4), and the
re-run-idempotent Ingest and Match writes (F2). The suite grew from 35 to 51
tests, all key-free; one run was driven through the API by hand. No live model
has ever been called. Concurrency stays unproven — built, tests deferred to
the concurrency slice. `DECISIONS.md` now carries every slice 1b lock and fix
decision, plus the four architecture-closing locks (network bind, review
re-entry, the five-section review screen, and the brief acceptance contract).

**2026-08-13 — Handoff design locks transcribed into the canonical documents**
Moved the finished design decisions from `handoff/` working files into the
canonical documents. `DECISIONS.md` gained the three architecture locks
(the six-tool MCP surface mirroring the API, the in-process MCP server with
validation owned by the core function, and one findings table with
run-frozen configuration) and the prompt-injection proof placement, each
with its Decision Log row and canonical section. `sample-projects/README.md`
now describes the Northside Dental second-run corpus. `config/README.md`
lists the three config files as present and records `model.yaml`'s `call:`
block. This status section now names slice 1a and slice 1b as merged. No
checklist item is ticked by this work — none of it completes a roadmap item.

**2026-08-12 — Phase 4 slice 1 proof and boilerplate planned**
Designed the four-document intake-portal demo corpus without creating its
files. Locked slice 1's three automated tests with a fake model and real
PostgreSQL, plus the Docker Compose run/test plan and startup migrations.
Added one Decision Log row for the test split; left unverified commands out of
`TASK.md` and the README.

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
