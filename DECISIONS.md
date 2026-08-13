# DECISIONS.md — current canonical decisions

This file answers **what is true now and why**. It is intentionally compact.
Detailed reasoning, rejected alternatives, and the original append-only
Decision Log live in [`documentation/decision-history.md`](documentation/decision-history.md).
Exact pre-compaction source is preserved in
[`documentation/history/DECISIONS-pre-compaction-2026-08-13-2e14c91.md`](documentation/history/DECISIONS-pre-compaction-2026-08-13-2e14c91.md).

The task requirements are interpreted separately in
`documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`.
Do not turn our choices into brief claims.

## How to maintain this file

- Root `DECISIONS.md` contains current truth only.
- Before changing a decision, append its old form, rationale, date, and
  supersession link to `documentation/decision-history.md`; then update root.
- Keep exact mapping tables where identity matters. Otherwise use: **Decision,
  Why, Must preserve, Evidence, Limitation/open, History**.
- Code, migrations, tests, and observed runs outrank a stale status sentence.
- Use the status labels below; never collapse built and proven into one claim.

## Status labels

| Label | Meaning |
|---|---|
| **Implemented and verified** | Present in live code and covered by an executed test or observed run |
| **Implemented, proof pending** | Present in code, but its claimed runtime guarantee is not yet demonstrated |
| **Locked, not implemented** | Current design decision for a later slice |
| **Open decision** | A material choice is deliberately unresolved |
| **Known limitation** | Accepted boundary or gap; do not silently design around it |
| **Superseded** | Historical only; replacement is current |

## Vocabulary

- **Register** — the Requirements-to-Delivery Register.
- **Row** — one register line tracing one requirement.
- **Requirement** — the client ask traced by one row.
- **Finding** — a rule violation raised for human review.
- **Rule** — one user-supplied statement of what should have been true.
- **Project** — one client engagement, continuing register, and source folder.
- **Batch** — the new or changed files one run picks up.
- **Run** — one processing cycle for one project batch.
- **Blocker** — work explicitly stopped by a missing answer or dependency.
- **Delivery Owner** — the provider-side operator and human reviewer.

Use these words in code, tests, logs, UI, and documentation. Do not substitute
`item`, `entry`, `record`, `pile`, or `request` for the concepts above.

## Current decision index

| ID | Decision family | Status | Canonical section |
|---|---|---|---|
| D01 | Deliverable, domain, user, and run scope | Implemented and verified in slice-1 scope | Product contract |
| D02 | Human-gate scope, actions, and review queue | Implemented and verified for slice-1 gates | Human review |
| D03 | Incremental batching, watched-folder trigger, and already-read rule | Mixed | Input and incremental updates |
| D04 | Formats, document types, and parsing | Mixed | Input and incremental updates |
| D05 | Register cells, statuses, attachments, citations, and exports | Mixed | Register and evidence |
| D06 | Audit trail and unchanged-row proof | Mixed | Register and evidence |
| D07 | Pipeline stages and conditional routes | Mixed | Pipeline |
| D08 | Extract, quote location, prompt injection | Mixed | Extract |
| D09 | Match, requirement identity, and granularity | Implemented and verified in slice-1 scope | Match |
| D10 | Rules, Examine, findings, and no-findings | Implemented and verified with the scripted model | Examine and findings |
| D11 | Model provider, retry, failure classification | Mixed | Model boundary and failure handling |
| D12 | State, checkpoints, node re-entry, and Extract-call idempotency | Mixed | Reliability and concurrency |
| D13 | Run identity, statuses, lock, and queue | Mixed | Reliability and concurrency |
| D14 | Database and API surface | Implemented and verified in slice-1 scope | Storage and interfaces |
| D15 | MCP and React surfaces | Locked, not implemented | Storage and interfaces |
| D16 | Logging, timing, and cost | Mixed | Operations |
| D17 | Repository layout, build order, tests, setup, and network bind | Mixed | Delivery plan and proof |

## Product contract

### D01 — deliverable, domain, user, and run

- **Decision:** The deliverable is a **Requirements-to-Delivery Register**;
  one row traces one client requirement. Stable rows make focused updates,
  machine use, item-level review, and byte-level preservation tractable.
- **Domain:** **Software Requirements-to-Delivery** — documents produced after
  a client starts sharing software requirements, while a Software Provider
  clarifies, builds/configures, delivers, and receives client testing feedback.
- **Boundary:** Pre-sales, demos, pricing, contracts, SOWs, invoices, payments,
  source-code execution, deployment, resource management, and CRM are outside.
- **User:** One provider-side **Delivery Owner** operates and reviews V1. The
  client supplies evidence but has no V1 login or approval role.
- **Run:** A project owns one continuing register. One run handles one complete
  submitted document batch for that project; unrelated projects never mix.
- **Must preserve:** Facts, not judgements. Surface documentation gaps,
  conflicts, blockers, and uncertainty; never silently decide which claim wins.
- **Evidence/status:** Slice 1 proves one `.md` batch through export. Wider
  domain, formats, second corpus, and incremental updates remain later proof.
- **History:** Detailed comparisons with narrative brief/report and earlier
  narrower domain/run definitions are in decision history.

### Domain conditions

| Condition | Current rule |
|---|---|
| Documentation gap | A meeting ask absent from written requirements is a gap, not automatically a conflict |
| Conflict | Incompatible claims are shown together; the system chooses neither |
| Blocker | Only explicit stopped work waiting on an answer/dependency counts |
| New detail | No semantic match creates a row; compatible detail enriches; incompatible detail uses conflict review |
| Testing feedback | Label `Passed`, `Defect`, `Change request`, or `Unclear` from evidence |
| Baseline correctness | Crash, data loss, failed core action, or false success is a defect even if unstated |

## Human review

### D02 — where the gate applies

The gate applies when the system makes a judgement or changes an existing
row's meaning. Copying a cited fact is not separately gated because final
export is always gated.

| # | Scenario | Gate? |
|---|---|---|
| 1 | Entirely new cited row, no uncertainty | No |
| 2 | Compatible evidence added to an existing row | No |
| 3 | New document changes an existing row's meaning | Yes |
| 4 | Possible match to an existing row | Yes |
| 5 | Conflict | Yes |
| 6 | User-rule finding | Yes |
| 7 | Deliverable-side finding | Yes |
| 8 | Explicit blocker fact | No |
| 9 | Suspicious instruction reported from a source | No |
| 10 | File skipped with reason | No |
| 11 | Focused incremental-update proposal | Yes |
| 12 | Final export/commit | Yes |
| 13 | Honest `No findings` result | No |

### Actions and persistence

- **Decision:** Every gated proposal has only **Approve** or **Reject**. The
  buttons act on the stated proposal, never resolve the underlying truth.
- **Reject:** Exclude the proposal from the register but retain it permanently
  in the run record. Only rejecting final export ends `closed without export`.
- **Known limitation:** A rejected finding does not automatically return when
  later evidence makes it stronger. Evidence that resolves it naturally stops
  the rule firing.
- **Review queue:** One `decisions` row stores the frozen question and answer.
  Its UUID is the API key; question and answer are never stored apart.
- **A finding's answer lives only here.** `findings` carries the `decision_key`
  of its gated question and no `review_state` of its own, because an answer may
  change until `finish-review` and a second copy would have to be kept in step
  on every edit. Findings raised by Examine reach this same queue as
  `kind = 'finding'`, so `finish-review` already refuses while one is
  unanswered.
- **Change window:** An answer may change until `finish-review`. That endpoint
  refuses unanswered decisions and atomically claims the transition before it
  launches graph continuation.
- **Review replay:** `review_finished_at` (migration `20260813_0004`) is the
  durable fact that stops a finished Review node reopening after a crash; the
  Review node and `submit_decision` both gate on it, not on status alone.
  Proven by `test_finished_review_does_not_reopen_on_resume` and
  `test_decision_refused_after_review_finished_even_if_status_regresses` in
  `tests/test_finish_review.py`.
- **Evidence:** Possible-match and export decisions, incomplete-review refusal,
  atomic finish claim, merge/reject, export paths, and the post-finish
  crash-replay window are tested.

## Input and incremental updates

### D03 — batch and trigger

- **Decision:** A batch contains every new or changed file waiting when a run
  starts. A changed file is read in full; untouched files are never re-read.
- **Removed file:** Deleting a watched file does not delete its historical rows.
- **Watcher:** Poll every 10 seconds and auto-start after 30 seconds of quiet,
  provided the project has no active run. Manual `POST /runs` remains.
  **Locked, not implemented.** Files arriving during Review wait for next run.
- **Rules-only run:** When parsed rules change, skip Extract/Match and run
  Examine against the existing register. **Locked, not implemented.**
- **Deletion semantics:** Whether removing a requirement from a changed
  document withdraws, deletes, or conflicts is an **open decision**.

### Already-read rule

A content-identical document counts as read only after extraction succeeded
and either:

1. its run exported a register; or
2. the extraction showed the document was unrelated or contained no
   requirement the register could take.

This keeps a transiently failed extraction eligible for the next run without
re-reading completed unrelated/no-requirement documents forever.

- **Evidence/status:** Implemented and verified by change-detection tests for
  transient failure, unrelated documents, and no-requirement documents.

### D04 — formats and document types

| Concern | Current contract | Status |
|---|---|---|
| Declared formats | `.pdf`, `.docx`, `.md`, `.txt` in `config/formats.yaml` | All four readers implemented and verified |
| Unsupported format | Skip with `unsupported format` reason | Implemented and verified |
| Page limit | 20 pages in config; oversized documents skip | Implemented in `app/ingest/read_source_document.py`; binds `.pdf` only |
| PDF | `pdfplumber` extraction, `pypdf` encryption check; scanned/encrypted skip | Implemented and verified for encrypted, scanned, and oversized skips |
| DOCX | `python-docx`, paragraphs and table cells in document order | Implemented and verified |
| TXT | UTF-8 with Latin-1 fallback | Implemented and verified |
| Folder scan | Top-level files only, read in place | Implemented for all four formats |

Format is checked before type. Type is a Pydantic enum at the model boundary,
and its buckets are:

| Bucket | Action | Status |
|---|---|---|
| Primary: meeting notes, client requirements document, testing feedback | Full declared processing | Implemented |
| Related additional | Read, labelled and stored; never creates a register row on its own | Implemented |
| Unrelated | Skip with reason | Implemented |
| Outside the enum | Skip that document with `document type not recognised`; the run continues | Implemented |

- **Must preserve:** Accepted-format list is config; actual readers are code;
  startup warns when config names a format with no reader.
- **Word text is copied, never marked up:** the DOCX reader adds no heading
  marker and no cell separator, because whatever it produces is both what the
  model reads as evidence and what a citation quotes back. Each table cell
  takes its own line, so a quote spanning two cells is not found and its
  requirement is dropped rather than supported by assembled words.
- **Damaged files are one document's problem:** a `.pdf` or `.docx` that no
  library can open is skipped with its reason, like an encrypted or scanned
  one, instead of ending the batch.
- **Limitation:** the page limit binds `.pdf` only, because only a paginated
  format can report a page count. Markdown, plain text and Word have none and
  none is invented for them; the shared gate in the dispatch limits any
  paginated reader added later.
- **Evidence:** `tests/test_document_readers.py`,
  `tests/test_document_type_buckets.py`, and one run over the six-document
  Northside Dental corpus.

## Register and evidence

### D05 — row shape

Seven cells, each with its own citations:

`What was asked` · `In writing?` · `What testing found` · `Status` ·
`Blocked on` · `First seen` · `Last moved`

Statuses are fixed in code:

`Done` · `Partial` · `Never happened` · `Blocked` · `Disputed` ·
`No evidence yet`

- `Never happened` is a positive evidenced claim; `No evidence yet` makes no
  such claim.
- Unknown cells say why they are unknown; they are never blank or guessed.
- Dates come from documents, not run time. Unknown date stays unknown and R3
  does not run on it.
- Conflicts, findings, and possible-match questions attach to rows but are not
  row cells. This preserves gate separation and cell-only fingerprints.
- **Implemented and verified:** Slice-1 proposal/commit/export shape and six
  statuses, plus finding attachments, which appear on the row in the export and
  leave its cells and fingerprint untouched.

### Citations

- Present evidence = source file + usable place + exact source words.
- Absence evidence = exact file read plus explicit absence statement.
- Locator by format: PDF page, Markdown nearest heading, DOCX line, TXT line.
  Do not invent DOCX page numbers.
- The model supplies exact words; code derives the place. Repeated words use
  the first occurrence.
- An unfindable quote drops that requirement and records a skip reason. Plain
  normalized substring matching is intentional; no fuzzy match.
- **Evidence/status:** Markdown quote location, multi-line normalization,
  invented quote rejection, first occurrence, and Latin-1 read are verified.
  The PDF page, DOCX line, and TXT line locators are implemented and verified
  by `tests/test_citation_places.py`; each citation may only name a place its
  own reader produced.
- **Limitation:** a DOCX line number counts lines of the text this system
  extracted, not lines Word displays, so a reader cannot open the file and
  jump to it — the quoted words remain the reliable way to find the passage.
  A Word citation names its heading only once headings can travel out of the
  reader without being written into the text; that is deferred, not refused.

### Export, audit, and fingerprints

- JSON is the record; Markdown is generated from it. Markdown is never edited
  as a second truth.
- Commit atomically writes approved rows, cell-level audit, fingerprints, and
  export. A fingerprint covers the seven cells only, excluding attachments.
- Audit answers: which cell/attachment, before, after, run, and source.
- **Implemented:** First-run cell audit and fingerprints are written; JSON and
  Markdown exports are verified.
- **Audit events:** `audit.event_kind` holds `cell change` or `attachment`
  (plain text plus a `CheckConstraint`, never a PostgreSQL `ENUM`).
  `cell_name` is nullable, and the seven-cell check applies only to a cell
  change; an attachment must name no cell, because a finding attaches to a row
  and there is no honest cell name to write. Migration `20260813_0005`
  backfills every existing row as a cell change; its downgrade drops
  attachment rows, which the older shape cannot represent. Proven by
  `tests/test_schema.py`.
- **Proof pending:** Later incremental slice must compare fingerprints and
  prove unaffected rows byte-identical.

## Pipeline

### D07 — stages and routes

Full locked pipeline:

`Ingest → Extract → Match → Examine → Review → Commit`

| Stage | Job | Model call | Current status |
|---|---|---|---|
| Ingest | Read new/changed supported files | No | Implemented and verified for all four formats |
| Extract | One document: type/date/requirements/testing/blockers/instructions | One per document | Implemented and verified with scripted model |
| Match | Whole batch against current register | One per batch | Implemented and verified with scripted model |
| Examine | Whole register against frozen rules | One per register | Implemented and verified with scripted model |
| Review | Present gated proposals and wait | No | Implemented and verified for slice-1 proposals |
| Commit | Atomic durable rows/audit/export | No | Implemented and verified |

All documents complete one stage before the batch moves on. Extract loops with
a per-document checkpoint. All six stages are built: Match routes to Examine
when it proposed a row and to the early exit when it did not, and Examine
always continues to Review.

Early exits are honest terminal `ended without changes` states with reasons:
no readable new/changed file; everything skipped; nothing traceable extracted;
or Match changes no register cell. A future rules-only change routes directly
to Examine rather than exiting.

## Extract

### D08 — one call, exact evidence, structural injection boundary

- **Decision:** One model call per document, sequentially. This makes filename
  attribution deterministic, checkpointing clean, and failures isolated.
- **Output:** type, date, requirements, testing observations, blockers, and
  embedded instructions, each tied to exact words. This list may widen only
  with a real later-slice need.
- **Injection:** Document text is data, never system authority. It has no code
  path to approve, commit, or export. The model may report suspicious text;
  detection is not guaranteed and no brittle phrase list is built.
- **Required proof:** Later behaviour-8 test must show hostile document text
  cannot record approval, commit, or export. A demo document also carries one
  buried hostile line; the second-run corpus does not.
- **Known limitation:** If killed after a model answer is stored but before its
  checkpoint, one call may repeat. Rows and finished earlier calls do not.

## Match

### D09 — identity, granularity, and safe answers

- Match sees the whole small register; no embedding shortlist. The current
  size assumption is about 15 rows/~250 tokens and remains unmeasured.
- One source item becomes one row. The system does not re-cut a client's
  bundled item; optional bundle flagging is deferred.
- Outcomes: new row, existing row, possible match. In slice 1 a confident
  existing-row answer is deliberately downgraded to human-reviewed possible
  match before evidence reaches a committed row.
- Every requirement index must return exactly once with a valid outcome and
  correct `row_number` presence. An incomplete answer fails the run; it never
  defaults to a guess.
- Approved merge moves citations to the candidate and marks the proposal with
  `merged_into_register_row_id`; it is retained and skipped by Commit. Reject
  keeps it as a separate proposed row. Row-number gaps are accepted.
- **Evidence/status:** Implemented and verified by coverage, duplicate-index,
  missing-row-number, merge, rejection, and node-rerun tests.
- **Open:** pgvector retrieval is unnecessary for current short documents; if
  still unused at submission, disclose the defended stack choice.

## Examine and findings

### D10 — rules and findings

- Rules live in user-editable `config/rules.yaml`; adding/changing a rule is a
  data change. Default R1–R4 cover written requirement, change request versus
  bug, blocker age, and missing testing outcome.
- Deliverable checks D1/D2 require every row to cite a source and forbid
  `Done` without a testing outcome.
- One findings table, no rules table. Each finding freezes rule id and text,
  found issue, evidence, row, and human question; its answer is read from the
  decision it names (D02), not stored again.
- Configuration is frozen per run. A fingerprint covers parsed rules, ignoring
  comments/whitespace. Per-rule change detection is deliberately not built;
  a rules change re-examines the whole small register in one model call.
- `No findings` is first-class and must state what actually ran; never
  manufacture a weak finding.
- **The frozen rules live on `runs`:** `rules_snapshot` (JSONB) and
  `rules_fingerprint`, not a separate table — `rules.yaml` is small and `runs`
  already carries JSONB. The whole snapshot is stored, not only the
  fingerprint, because an honest `No findings` result must name what actually
  ran and a run with no findings has that rule text nowhere else. Ingest
  freezes it once, guarded on `rules_snapshot IS NULL`, so a resumed run reads
  what it froze rather than the file.
- **Who computes what:** R1–R4 are judged by the model in one Examine call;
  the deliverable checks D1 and D2 are computed in code, because each is a
  mechanical fact about the stored register — a row's citations are there or
  they are not. An unusable rules file fails the run at the boundary and is
  never read as "no rules".
- **`examined_row_count` on `runs`** records how many rows Examine judged, so
  the `No findings` result can state it after the run ends and whether or not
  an export exists.
- **Status:** Implemented and verified with the scripted model. Findings reach
  the human gate through the existing review queue, a rejected finding stays in
  the run record and never reaches the export, and Examine re-entry after a
  crash replaces this run's unanswered findings rather than adding to them.
  Proven by `tests/test_examine_findings.py`, `tests/test_examine_answer.py`,
  `tests/test_frozen_rules.py`, `tests/test_deliverable_checks.py`, and
  `test_examine_rerun_does_not_duplicate_findings_for_the_same_run`.

## Model boundary and failure handling

### D11 — provider and injected client

- OpenRouter through its OpenAI-compatible API; model/base URL/rates/call
  settings live in `config/model.yaml`; key comes only from environment.
- One client is constructed centrally and injected into stages. Tests use the
  deterministic scripted client and require no provider or key.
- **Status:** Client/config path implemented; no live model has been called.
  Default model quality, real SDK exception shapes, cost, and latency remain
  unverified.

### Failure contract

| Failure | Treatment |
|---|---|
| PostgreSQL unavailable | Stop; name database cause and fix |
| File/folder unreadable | Skip that file with reason; continue |
| Extract transient failure after attempts | Skip that document; next run retries it |
| Match/Examine failure | Stop `failed`; no smaller safe unit exists |
| 401/403 | Stop; valid key required |
| 402 | Stop; account lacks credits |
| 404 | Stop; fix model id |
| Timeout, 429, 500/502/503, network | Retry according to client/config, then stage rule above |
| Malformed/incomplete answer | Extract may skip; Match fails rather than guesses |

Classify provider failures by typed/status-code data, never message text.
Configuration failures must not degrade into every document skipped and a
false-success `done` run.

- **Locked policy:** two total attempts, nominal five-second wait, 120-second
  per-attempt timeout.
- **Known deviation/assumption:** Code delegates retry timing to the OpenAI
  SDK; the exact fixed five-second wait is not implemented. This is already
  declared, not a new finding.
- **Evidence:** Scripted timeout/401 paths and failure statuses are tested;
  live provider behaviour remains unverified.

## Reliability and concurrency

### D12 — state, checkpoints, and node re-entry

- LangGraph raw `StateGraph`; state holds progress and database pointers, not
  duplicated document/register material. PostgreSQL stores checkpoints and
  domain tables in one database.
- Ingest has no per-file graph checkpoint; Extract checkpoints after every
  document. Domain writes complete before LangGraph writes its checkpoint.
- Therefore a killed node may re-enter. Ingest upserts by `(run_id,
  source_path)` and returns existing ids; Match clears only its own uncommitted
  proposals/citations/unanswered decisions, then writes fresh in one
  transaction. Extract's update is harmless to repeat.
- Commit is atomic. Review decisions write directly to DB; graph state answers
  where execution is, DB answers what was decided.
- Startup resumes `running` runs from checkpoints; deliberate `failed` runs do
  not resume.
- **Evidence/status:** Real child-process `SIGKILL` resume, Ingest/Match
  re-entry, and the `review_finished_at` replay guard are verified.

### D13 — identity, queue, and statuses

- Run UUID is also LangGraph `thread_id`.
- One active run per project is enforced durably in PostgreSQL. A second run
  returns one `waiting` run; its batch is formed only when it starts. Different
  projects may run concurrently.
- Slice 1 executes background work inside one FastAPI process. A separate
  worker is a legitimate later change; database locks preserve correctness.
- Run statuses: `waiting`, `running`, `waiting for review`, `done`, `closed
  without export`, `failed`, `ended without changes`.
- `done` means export exists. `closed without export` means export was rejected.
  `failed` is deliberate unrecoverable stop. Early exits use `ended without
  changes` plus a reason.
- **Implemented, proof pending:** Lock and queue exist; kill/resume exercises
  the lock indirectly. Dedicated same-project queue and two-project isolation
  tests belong to the concurrency slice. Do not call concurrency proven yet.
- **Known limitation:** A run at Review holds the project lock as long as the
  Delivery Owner takes; later work waits.

## Storage and interfaces

### D14 — database and API

Eight domain tables: `projects`, `runs`, `documents`, `register_rows`,
`citations`, `decisions`, `audit`, `findings`. LangGraph owns separate
checkpoint tables in the same PostgreSQL. Alembic migrations exist from the
first table.

Six slice-1 API endpoints:

| Endpoint | Job |
|---|---|
| `POST /projects` | Create project from name + source folder |
| `POST /runs` | Start/queue run by project id; return immediately |
| `GET /runs/{id}` | Durable status, stage, skips, failure, decisions |
| `POST /runs/{id}/decisions` | Answer one decision UUID |
| `POST /runs/{id}/finish-review` | Validate/claim review completion |
| `GET /runs/{id}/export` | Approved JSON or Markdown export |

Startup seeds the demo project only when `projects` is empty, using the same
core creation function as the endpoint. **Implemented and verified** in
slice-1 scope.

### D15 — MCP and React

- MCP will mirror the six endpoints 1:1: `create_project`, `start_run`,
  `get_run_status`, `submit_decision`, `finish_review`, `get_export`.
- It mounts in the FastAPI process and calls the same core functions directly.
  Validation/error semantics belong in core, not only HTTP adapters.
- React is one page with five sections: stages, skipped, needs your decision,
  register, cost/timing. One generic question component serves all gates.
- No blanket approve tool, waiting wrapper, separate MCP logic, state library,
  design system, dashboard, settings, or charts.
- **Status:** Locked, not implemented. Layout/visual treatment remains open.

## Operations

### D16 — logging, timing, and cost

- JSON-line stdout logs; every run event carries `run_id`. Log stage start/end,
  path-changing decisions, retries, and failures. Never log secrets or full
  document text.
- Each stage records duration; run reports stage breakdown and total.
- Estimated cost = model-reported tokens × configured rates, clearly labelled
  estimate rather than bill.
- **Current status:** Structured run events exist. Schema has timing/cost
  fields, but collection, roll-up, API reporting, measurements, and proof are
  not implemented. No measured model timing/cost exists.

## Delivery plan and proof

### D17 — repository and build order

- Runnable material stays at root (`app`, `tests`, `migrations`, `config`,
  `sample-projects`); background reading stays under `documentation/`.
- Build thin end-to-end slices, risky runtime properties first, UI last.
- Slice 1 is complete: `.md` Ingest → Extract → Match → Review → Commit,
  PostgreSQL, six endpoints, human gate, export, and real-process resume.
- The formats and types slice is built: four readers, the page limit, the
  document-type enum and its buckets, per-format citation places, and both
  synthetic corpora.
- The rules and findings slice is built: Examine, the `findings` table, rules
  frozen per run, D1/D2 in code, and the attachment audit event.
- Later slices: MCP → incremental proof → concurrency/
  injection → React → cost/timing. Exact scheduling may combine safe adjacent
  work, but proof claims stay separate.

### Brief-behaviour acceptance summary

| # | Behaviour | Minimum proof | Current status |
|---|---|---|---|
| 1 | Visible branching stages | Status output plus uncertain-match route | Verified across all six stages |
| 2 | Stop/resume | Real `SIGKILL`, startup resume, no repeated finished work/rows | Verified in slice 1 |
| 3 | Human gate | Mixed decisions, incomplete-review refusal, export gate | Verified in slice 1 scope |
| 4 | Machine drive | Full API flow, then same flow through MCP | API half verified; MCP later |
| 5 | Never bluff | Unfindable quote rejected; unknown status honest | Citation half verified |
| 6 | Stranger runs | Fresh clone, exact README commands, expected outcome | Open |
| 7 | Automated proof | Key-free full suite with real paths | 93 tests verified; later minima remain |
| 8 | No document authority | Hostile document cannot approve/commit/export | Locked, not implemented |
| 9 | Concurrent isolation | Two projects parallel; same project queues | Mechanism built, proof pending |
| 10 | Cost/time visibility | Per-stage duration + estimated cost from configured rates | Locked, not implemented |

### Slice-1 test and setup contracts

- Required core tests use the scripted model and real PostgreSQL. Kill proof
  uses a separate process and real `SIGKILL`, not an in-process exception.
- Verified development test command: `docker compose run --rm app pytest`.
  Fresh-clone proof is still open; do not present it as completed.
- Planned run is `docker compose up`; migrations run on startup. A live run
  needs an OpenRouter key, tests do not.
- **Network bind:** Loopback-only host exposure is implemented: the
  Dockerfile's `uvicorn` reads `APP_HOST`, defaulting to `127.0.0.1`; Compose
  sets `APP_HOST=0.0.0.0` for the app service (required inside the container)
  and publishes `127.0.0.1:8000:8000`, matching `db`. Proven by
  `tests/test_loopback_bind.py`.
- **Known development limitation:** Broad `.:/workspace` bind mount is retained
  for iteration. Remove/narrow it and clear stale dev DB before final
  image-only verification.

## Open decisions

1. Task 2 orchestration: high-level `create_agent` versus raw StateGraph.
2. Changed-document deletion/withdrawal semantics.
3. Whether review answers stay one-at-a-time or later batch at the API layer.
4. React visual layout and treatment (content/gates are locked).
5. Whether real document sizes justify pgvector retrieval or Extract fan-out.
6. Exact later-slice storage choices where this file explicitly leaves them
   open; do not invent them before their slice.

## Known limitations and unverified assumptions

- No live model call has run; provider quality, exception shapes, latency, and
  cost are unverified.
- Register-size and short-document assumptions remain unmeasured on full demo
  and second-run corpora.
- The page limit binds `.pdf` only; no other declared format reports pages.
- A related additional document that lists requirements, in a run that never
  exports, is read again by the next run.
- Concurrency mechanism is built but dedicated proof is pending.
- One Extract call can repeat in the answer-to-checkpoint kill window.
- Rejected findings stay suppressed even if later evidence strengthens them.
- Files arriving during Review wait; the project lock may be held a long time.
- Oversized PDFs are skipped rather than chunked, and scanned PDFs are skipped
  rather than read; chunking and OCR are not planned for V1.
- Watched folder, MCP, React, incremental unchanged-row proof, and cost/timing
  are locked but not implemented.
- A finding raised against a register row is never re-examined by a later run;
  a rules change re-examines the register the next run touches it.

## Superseded index

The exact rows and reasons remain in decision history. This index prevents old
ideas from resurfacing without duplicating their full prose here.

| Superseded family | Current replacement |
|---|---|
| Register/table initial proposal | D01 reviewed Requirements-to-Delivery Register |
| Hard-coded accepted-format gate | D04 config list + code readers + startup reconciliation |
| Known/related-unknown/unrelated | D04 primary/related additional/unrelated |
| Software feature delivery/customer/dev team | D01 Software Requirements-to-Delivery/Client/Software Provider |
| Feature request list primary type | D04 client requirements document |
| Blocker as document type/undecided representation | D01 condition + D05 status and `Blocked on` |
| One run equals one project | D01 project context + document-batch run |
| Manual-only run trigger | D03 auto-start watcher plus manual endpoint |
| Five register statuses | D05 six statuses including `No evidence yet` |
| Location always derived without caveat | D05/D08 exact-word locator with repeated-word limitation |
| Empty-input Ingest always ends | D03/D07 rules-only route to Examine |
| Five API endpoints | D14 six endpoints including project creation |
| `done` as generic terminal state | D13 honest `failed`/`ended without changes`/`closed without export` |
| Status-only already-read check | D03 extraction + export/unrelated/no-requirement rule |
| Unmarked emptied merge proposal | D09 `merged_into_register_row_id` |
| Missing Match outcomes default to new rows | D09 complete exact coverage or failure |
| Non-atomic finish-review read/launch | D02 atomic claim plus future replay marker |
| Non-idempotent Ingest/Match re-entry | D12 unique/upsert Ingest + replace-own-uncommitted Match |
| `audit.cell_name NOT NULL` for every event | D06 `event_kind` with a nullable cell name for attachments |

For full chronology, alternatives, trade-offs, evidence language, and all 93
original Decision Log rows, use `documentation/decision-history.md`.
