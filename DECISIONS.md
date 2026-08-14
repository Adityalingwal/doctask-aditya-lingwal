# DECISIONS.md — current canonical decisions

This file answers **what is true now and why**. It is intentionally compact.
Detailed reasoning, rejected alternatives, and the original append-only
Decision Log live in [`documentation/decision-history.md`](documentation/decision-history.md).
Exact pre-compaction source is preserved in
[`documentation/archive/history/DECISIONS-pre-compaction-2026-08-13-2e14c91.md`](documentation/archive/history/DECISIONS-pre-compaction-2026-08-13-2e14c91.md).

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
| D03 | Incremental batching, watched-folder trigger, already-read rule, and withdrawal | Implemented and verified | Input and incremental updates |
| D04 | Formats, document types, and parsing | Mixed | Input and incremental updates |
| D05 | Register cells, statuses, attachments, citations, and exports | Mixed | Register and evidence |
| D06 | Audit trail and unchanged-row proof | Implemented and verified | Register and evidence |
| D07 | Pipeline stages and conditional routes | Mixed | Pipeline |
| D08 | Extract, quote location, prompt injection | Mixed | Extract |
| D09 | Match, requirement identity, and granularity | Implemented and verified in slice-1 scope | Match |
| D10 | Rules, Examine, findings, and no-findings | Implemented and verified with the scripted model | Examine and findings |
| D11 | Model provider, retry, failure classification | Mixed | Model boundary and failure handling |
| D12 | State, checkpoints, node re-entry, and Extract-call idempotency | Mixed | Reliability and concurrency |
| D13 | Run identity, statuses, lock, and queue | Implemented and verified | Reliability and concurrency |
| D14 | Database and API surface | Implemented and verified in slice-1 scope | Storage and interfaces |
| D15 | MCP and React surfaces | MCP implemented and verified; the redesigned screen is implemented, proof pending against the application | Storage and interfaces |
| D16 | Logging; timing and cost dropped | Logging implemented and verified; timing and cost removed from the screen and from the application | Operations |
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
- **One answer at a time, and no batch — locked 2026-08-14.** Every proposal is
  answered by its own request; there is no "approve all" and no endpoint that
  takes several answers together. A batch would need a second API shape, a
  second MCP tool, and an answer to a question V1 does not otherwise have —
  what a partly failed batch means when three of seven answers do not apply.
- **Trade-off, stated plainly:** a run holding many gates costs the Delivery
  Owner one click and one request each. That is accepted. Reading each proposal
  before answering it is the point of the gate, and a screen that lets someone
  approve seven at once quietly invites approving without reading.
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
  `tests/register/test_finish_review.py`.
- **Evidence:** Possible-match and export decisions, incomplete-review refusal,
  atomic finish claim, merge/reject, export paths, and the post-finish
  crash-replay window are tested.

## Input and incremental updates

### D03 — batch and trigger

- **Decision:** A batch contains every new or changed file waiting when a run
  starts. A changed file is read in full; untouched files are never re-read.
- **Removed file:** Deleting a watched file does not delete its historical rows.
- **Watcher:** Poll every 10 seconds and auto-start after 30 seconds of quiet,
  provided the project has no run running, at review, or queued. Manual
  `POST /runs` remains. Files arriving during Review wait for the next run.
  Both numbers are `config/watcher.yaml`, read through `WATCHER_CONFIG_PATH`.
  **Implemented and verified** by `tests/runs/test_watched_folder.py`.
- **Baseline, not backlog:** whatever the watcher first sees in a folder is not
  an arrival, so a project created over a folder of documents starts nothing by
  itself and never surprises a fresh `docker compose up` with a paid run. The
  cost is that a restart forgets what it saw; see PROGRESS limitations.
- **Rules-only run:** When the rules a run froze differ from the ones the
  register was last examined against and no document changed, skip
  Extract/Match and run Examine against the existing register. It is the same
  run object, routed differently. **Implemented and verified** by
  `test_a_changed_rules_file_re_examines_the_register_without_reading_a_document`.
- **Unchanged-row proof:** a second run leaves every row its documents did not
  affect byte-identical — cells, citations and fingerprint. **Implemented and
  verified** on both synthetic corpora by
  `tests/incremental/test_second_run_on_corpora.py` and
  `tests/incremental/test_incremental_updates.py`.

### Withdrawal — when a changed document drops a requirement

- **Decision:** A re-read document that no longer contains a requirement it
  itself supplied raises one **withdrawal proposal** for that row. Approve
  moves that row's `Status` cell to `Withdrawn` and records absence evidence;
  Reject leaves the row byte-identical. The row is never deleted.
- **What may trigger it:** only the changed document whose words the row's
  `What was asked` citation quotes, and only when that document's new
  extraction yields neither a match nor a possible match for the row. Another
  document's silence proposes nothing, because absence of mention is not
  evidence of removal.
- **Why not delete:** deleting contradicts the removed-file rule above and
  empties the row's audit history, `First seen`, and fingerprint chain.
- **Why not a conflict:** a conflict is two sources disagreeing. Here nothing
  contradicts anything; something stopped being asked for.
- **Gate:** the existing review queue as `kind = 'withdrawal'`, one decision
  per row, Approve or Reject only — D02 scenario 3.
- **Must preserve:** an approved withdrawal is a `Status` cell change, so it
  writes cell audit and moves only that row's fingerprint; a rejected one is
  retained in the run record and is not raised again until that document
  changes again; the absence is cited to the document the question named,
  which the decision stores, never to one worked out again afterwards.
- **A withdrawal is final in V1.** If a later document asks for the
  requirement again, its evidence merges onto the row as any evidence does,
  and the row still reads `Withdrawn`. Nothing in this system updates a
  committed row's cells from later evidence — an approved match moves
  citations only — so there is no ordinary gate to carry it back, and no
  honest status to carry it to: `No evidence yet` would deny testing evidence
  the row may already hold, and the status it had before the withdrawal
  described a world that has since changed. Deciding what a returning
  requirement should read as is deferred, not refused.
- **Limitation:** `Withdrawn` describes the requirement, while the other six
  statuses describe delivery. One `Status` cell carries both, because it is
  the one cell every export, gate, and reader already consults.
- **Detection costs no model call:** Match already reports what the changed
  document's new extraction matched, so a row that document supplied with
  neither a match nor a possible match in that output is the candidate. Asking
  a model "was this removed?" would be a second answer to a question the
  pipeline has already answered, free to disagree with the first.
- **Suppression is the trigger itself:** a rejected withdrawal is not raised
  again because the document is not read again until it changes again. No
  second piece of state remembers the rejection.
- **Status:** **Implemented and verified** — 2026-08-14. Ours, not the brief's;
  the task PDF says nothing about removed requirements. Proven by
  `tests/register/test_withdrawal.py` and
  `test_the_re_issued_corpus_requirements_document_withdraws_the_row_it_dropped`,
  including the answer submitted through the MCP `submit_decision` tool.
- **History:** [`decision-history.md`](documentation/decision-history.md),
  "Withdrawing a requirement a changed document dropped".

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
- **Evidence:** `tests/documents/test_document_readers.py`,
  `tests/documents/test_document_type_buckets.py`, and one run over the
  six-document Northside Dental corpus.

## Register and evidence

### D05 — row shape

Seven cells, each with its own citations:

`What was asked` · `In writing?` · `What testing found` · `Status` ·
`Blocked on` · `First seen` · `Last moved`

Statuses are fixed in code and in a database check constraint:

`Done` · `Partial` · `Never happened` · `Blocked` · `Disputed` ·
`No evidence yet` · `Withdrawn`

- `Never happened` is a positive evidenced claim; `No evidence yet` makes no
  such claim.
- `Withdrawn` is set only by an approved withdrawal proposal (D03).
  **Implemented and verified**; migration `20260814_0007` widened
  `REGISTER_ROW_STATUS_CHECK` and `ck_decisions_kind` together, and its
  downgrade refuses rather than force a withdrawn row into a status that would
  claim something its evidence does not support.
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
  by `tests/documents/test_citation_places.py`; each citation may only name a
  place its own reader produced.
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
  `tests/infrastructure/test_schema.py`.
- **Implemented and verified:** a second run's unaffected rows come back with
  the same cells, the same citations and the same fingerprint, compared as
  stored rather than as rendered. An approved merge moves citations onto the
  candidate row without moving its fingerprint, because a citation is not a
  cell.
- **Withdrawal writes the first absence citation this system has produced:** no
  quote, so no `locate_quote` and no place — `source_place` and `source_words`
  stay null and the statement names the file and what is not in it.

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
or Match neither proposes a row nor proposes a withdrawal. Ingest routes
straight to Examine instead when no document changed but the rules did, and
Extract routes on to Match even with no requirement found when the batch read a
document some committed row was asked for in — a document that dropped its last
requirement is exactly what a withdrawal is for. Match makes no model call when
there is nothing to match.

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
- **Implemented and verified** — 2026-08-14, by
  `tests/documents/test_document_instruction_is_reported.py`, which drives the
  demo document that buries the hostile line through a real run: the line is
  stored as an embedded instruction placed in that document and logged against
  the run, and it creates no row, changes no cell, reaches the Delivery Owner
  as no proposed action, and appears nowhere in the export. The export was
  still refused until a person approved it.
- **What that proof does not cover:** the model is scripted, so this shows the
  pipeline has no path from document text to an approval, a commit or an
  export. Whether a live model spots the line is the detection the decision
  above already declines to guarantee.
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
  Proven by `tests/examine/test_examine_findings.py`,
  `tests/examine/test_examine_answer.py`,
  `tests/examine/test_frozen_rules.py`,
  `tests/examine/test_deliverable_checks.py`, and
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
- **Implemented and verified** — 2026-08-14, by
  `tests/runs/test_two_projects_at_once.py` and
  `tests/runs/test_same_project_queue.py`,
  against real PostgreSQL and the scripted client:
  - Two projects run at once and neither reaches into the other — row,
    citation, decision, finding and log line each belong to the run that
    produced them. The two runs are shown to have been live together twice
    over: both reported `running` with a stage set at one polled moment, and
    two of their model calls started less than the scripted call delay apart,
    so those calls were in flight together.
  - A second run on one project is `waiting`, however often it is asked for,
    while the first holds the lock in either active status.
  - A waiting run's batch is formed when it starts: a file that arrived while
    it waited belongs to it, and to the run ahead of it never.
  - The run behind is not lost when the one ahead ends, whether that ending is
    `done` or `failed`.
- **Known limitation:** A run at Review holds the project lock as long as the
  Delivery Owner takes; later work waits.

## Storage and interfaces

### D14 — database and API

Eight domain tables: `projects`, `runs`, `documents`, `register_rows`,
`citations`, `decisions`, `audit`, `findings`. LangGraph owns separate
checkpoint tables in the same PostgreSQL. Alembic migrations exist from the
first table.

Seven slice-1 API endpoints:

| Endpoint | Job |
|---|---|
| `POST /projects` | Create project from name + source folder |
| `POST /runs` | Start/queue run by project id; return immediately |
| `GET /runs` | Every run, newest first: project, status, start time, waiting decisions, finished stages |
| `GET /runs/{id}` | Durable status, stage, skips, failure, decisions |
| `POST /runs/{id}/decisions` | Answer one decision UUID |
| `POST /runs/{id}/finish-review` | Validate/claim review completion |
| `GET /runs/{id}/export` | Approved JSON or Markdown export |

Startup seeds the demo project only when `projects` is empty, using the same
core creation function as the endpoint. **Implemented and verified** in
slice-1 scope.

### D15 — MCP and React

- MCP mirrors the seven endpoints 1:1: `create_project`, `start_run`,
  `list_runs`, `get_run_status`, `submit_decision`, `finish_review`,
  `get_export`.
- It mounts in the FastAPI process at `/mcp` and calls the same core functions
  the endpoints call. Existence checks, refusals and the shape a caller is told
  live in core, so a door decides only how to carry a refusal, never what it
  says: `UnknownId`, `NotPossibleNow`, `UnusableRequest` and `RunsUnavailable`
  become 404, 409, 400 and 503 over HTTP and reach a tool caller as the same
  sentence.
- The dependency is the official `mcp` SDK pinned at `1.29.0`. Its 2.x line was
  days old and changes the HTTP stack it depends on; `fastmcp` would put a
  second server framework beside FastAPI.
- React is one screen filling the viewport: a run list down the left, and to its
  right one run's sections read one at a time behind tabs — stages, skipped,
  needs your decision, register. One generic question component serves all
  gates, with no branch on gate kind. The two columns scroll independently.
- The run list replaces pasting a run id: a card carries the project name, when
  the run started, which stages finished and what is waiting, and never a UUID.
  Section tabs carry `role="tab"`, not the button role, because choosing what to
  read is navigation — the only actions on a run stay Approve, Reject and
  Finish review.
- **The stage strip's own stage wins over "done" only while the run is active**
  (`running` or `waiting for review`). Extract writes its finished mark after
  every document, not just the last one, so a batch's own stage can read
  "finished" before the batch is done; the run's current stage overrides that
  reading while the run is still working, but a `done`, `failed`, or otherwise
  terminal run shows its last stage as `done`, not stuck "working" forever.
- No blanket approve tool, waiting wrapper, separate MCP logic, state library,
  design system, dashboard, settings, or charts.
- The screen reads `GET /runs/{id}` on a poll whose interval is
  `ui/config/screen.json`, and reads `GET /runs/{id}/export` only once that
  status says the run exported. Nothing a person clicked is shown: an answer is
  posted and the screen then re-reads the run it was recorded against.
- The screen's own toolchain is Vite and Vitest with jsdom and
  `@testing-library/react`, all pinned exactly. React and `react-dom` remain the
  only runtime dependencies. **Tailwind CSS 4.3.3 is installed** as a build-time
  dependency, with the palette, the two fonts and the spacing held as `@theme`
  tokens in `ui/src/screen.css`; IBM Plex Sans and IBM Plex Mono are served from
  the repository through `@fontsource`, latin subset only, so the screen fetches
  no font at runtime. No state library, component library or icon set is
  installed, and there is still no design system.
- FastAPI serves the built screen at `/ui` from `ui/dist`
  (`app/review_screen/serve_screen.py`). Node is not in the image, so an
  unbuilt checkout is answered `503` naming the build command rather than a
  bare `404`.
- **Status:** MCP **implemented and verified** — `tests/interfaces/test_mcp_tools.py`
  and `tests/interfaces/test_mcp_flow.py`, plus one run driven through the tools by hand.
  React is **implemented, proof pending** for the redesigned screen: twenty
  Vitest cases in `ui/tests/` and the two route cases in
  `tests/interfaces/test_review_screen_route.py` pass, but the screen has only been driven
  against `ui/demo/`, never against the application since the redesign. Layout
  and visual treatment are no longer open. Answering one decision at a time is
  locked in D02, and the screen must not offer any approve-all or batch-submit
  affordance.
- `GET /runs` and `list_runs` are built, both calling `app/runs/list_runs.py`'s
  one core function: every run, newest first, no cap, each carrying its
  project name, status, `started_at` (`null` for a run that has not started
  — never substituted with `created_at`), the count of unanswered decisions,
  and `finished_stages` as an ordered list of stage names.
- Limitation: `GET /runs/{id}` carries no register rows, so the register
  section is empty until the run has exported.
- Limitation: the tools inherit the HTTP surface's lack of authentication, and
  the SDK's own host check answers `421` to a request whose `Host` is neither
  `localhost` nor `127.0.0.1`, so a client on another machine needs transport
  work that is not designed yet.

## Operations

### D16 — logging

- JSON-line stdout logs; every run event carries `run_id`. Log stage start/end,
  path-changing decisions, retries, and failures. Never log secrets or full
  document text.
- **Timing and cost are dropped, not deferred (2026-08-14).** They cost a
  column set, a migration, a module, a test file and a section of screen, and
  returned a figure that was never a provider charge. Nothing in the
  application any longer records a duration, a token count or a cost, on a
  log line or anywhere else — this phase cut that scope rather than adding to
  it. `app/runs/cost_and_timing.py`, `tests/runs/test_timing_and_cost.py`,
  the `runs.stage_timings`, `runs.token_usage`, `runs.estimated_cost_usd` and
  `runs.cost_unknown_reason` columns (migration `20260814_0010`), the
  `usage_metadata` read in `app/model/call_the_model.py`, and
  `rates_usd_per_token` in `config/model.yaml` are all gone. History in
  `documentation/decision-history.md`.
- **What replaced it: `runs.finished_stages`.** A jsonb object keyed by stage
  name only (`{"ingest": true, "extract": true, ...}`), written where each
  stage's pass ends with the same `||` merge the dropped `stage_timings` used,
  so a node that re-enters after a kill (D12) overwrites its own key instead
  of adding a second one. `read_run_status` and `GET /runs`/`list_runs` both
  report it as an ordered list of stage names
  (`app/runs/finished_stages.py:ordered_finished_stages`), never the keyed
  object and never the keys unordered.
- **Why not derive it from `runs.stage` instead:** on the rules-only route
  Ingest goes straight to Examine, so Extract and Match never execute; reading
  the answer off `runs.stage` alone would call them finished the moment the
  run reached a later stage. `finished_stages` records only what actually ran.
- **Status:** Complete. Logging is JSON-line stdout with `run_id` on every
  event; no timing, cost, or usage data exists anywhere in the application.

## Delivery plan and proof

### D17 — repository and build order

- Runnable material stays at root (`app`, `tests`, `migrations`, `config`,
  `sample-projects`); background reading stays under `documentation/`.
- Build thin end-to-end slices, risky runtime properties first, UI last.
- Slice 1 is complete: `.md` Ingest → Extract → Match → Review → Commit,
  PostgreSQL, its six endpoints, human gate, export, and real-process resume.
- The formats and types slice is built: four readers, the page limit, the
  document-type enum and its buckets, per-format citation places, and both
  synthetic corpora.
- The rules and findings slice is built: Examine, the `findings` table, rules
  frozen per run, D1/D2 in code, and the attachment audit event.
- The MCP slice is built: its six tools mounted in the same process over the
  same core functions the endpoints call.
- The incremental update slice is built: the watched folder, the rules-only
  route, requirement withdrawal, and the byte-identical unchanged-row proof on
  both corpora. It added no tool; a withdrawal is another decision the existing
  decision tools carry.
- The reliability slice is built, and it is proof rather than construction: the
  concurrency and injection tests were written against the lock, the queue and
  the Extract path exactly as the earlier slices left them, and none of them
  needed a line of that code changed.
- The operations slice was built and then cut back: its timing and cost are
  dropped (D16), leaving structured run logging as what it contributed.
- `GET /runs` and its `list_runs` tool complete the seventh surface on both
  doors, and `runs.finished_stages` replaced what the dropped timings were
  being read for. Every planned slice is now built; what remains is the open
  fresh-clone and image-only verification and the first live-model run.

### Brief-behaviour acceptance summary

| # | Behaviour | Minimum proof | Current status |
|---|---|---|---|
| 1 | Visible branching stages | Status output plus uncertain-match route | Verified across all six stages |
| 2 | Stop/resume | Real `SIGKILL`, startup resume, no repeated finished work/rows | Verified in slice 1 |
| 3 | Human gate | Mixed decisions, incomplete-review refusal, export gate | Verified in slice 1 scope |
| 4 | Machine drive | Full API flow, then same flow through MCP | Both halves verified |
| 5 | Never bluff | Unfindable quote rejected; unknown status honest | Citation half verified |
| 6 | Stranger runs | Fresh clone, exact README commands, expected outcome | Open |
| 7 | Automated proof | Key-free full suite with real paths | 130 Python and 13 front-end tests verified; later minima remain |
| 8 | No document authority | Hostile document cannot approve/commit/export | Verified on the demo document that buries the line |
| 9 | Concurrent isolation | Two projects parallel; same project queues | Verified for both halves |
| 10 | Cost/time visibility | Per-stage duration + estimated cost from configured rates | Verified with the scripted client; no provider cost measured |

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
  `tests/infrastructure/test_loopback_bind.py`.
- **Known development limitation:** Broad `.:/workspace` bind mount is retained
  for iteration. Remove/narrow it and clear stale dev DB before final
  image-only verification.

## Open decisions

1. Task 2 orchestration: high-level `create_agent` versus raw StateGraph.
2. Nothing open here: the screen's layout and visual treatment were settled
   on 2026-08-14 with the run list, the section tabs and the Tailwind tokens.
3. Whether real document sizes justify pgvector retrieval or Extract fan-out.
4. Exact later-slice storage choices where this file explicitly leaves them
   open; do not invent them before their slice.

## Known limitations and unverified assumptions

- No live model call has run; provider quality, exception shapes, latency, and
  cost are unverified.
- Register-size and short-document assumptions remain unmeasured on full demo
  and second-run corpora.
- The page limit binds `.pdf` only; no other declared format reports pages.
- A related additional document that lists requirements, in a run that never
  exports, is read again by the next run.
- One Extract call can repeat in the answer-to-checkpoint kill window.
- Rejected findings stay suppressed even if later evidence strengthens them.
- Files arriving during Review wait; the project lock may be held a long time.
- Oversized PDFs are skipped rather than chunked, and scanned PDFs are skipped
  rather than read; chunking and OCR are not planned for V1.
- Timing and cost are dropped (D16). Nothing reports a duration, a token count
  or a cost; which stages a run finished is read from `runs.finished_stages`.
- The review screen is built by Node, which the application image does not
  carry, so `ui/dist` must be built before the screen can be served.
- The watcher holds what it last saw in memory, so a restart re-baselines every
  folder and a file that arrived while the application was down starts no run
  of its own.
- A row two documents both supplied raises a withdrawal proposal when either of
  them drops it; the proposal is a question, never a change.
- A withdrawal is final: a requirement asked for again merges its evidence onto
  the row, which still reads `Withdrawn`.
- Neither door authenticates a caller, and the MCP endpoint answers `421` to a
  `Host` header other than `localhost` or `127.0.0.1`.
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
| Five register statuses | D05 seven statuses including `No evidence yet` and `Withdrawn` |
| Location always derived without caveat | D05/D08 exact-word locator with repeated-word limitation |
| Empty-input Ingest always ends | D03/D07 rules-only route to Examine |
| Five/six API endpoints | D14 seven endpoints including `GET /runs` |
| `done` as generic terminal state | D13 honest `failed`/`ended without changes`/`closed without export` |
| Status-only already-read check | D03 extraction + export/unrelated/no-requirement rule |
| Unmarked emptied merge proposal | D09 `merged_into_register_row_id` |
| Missing Match outcomes default to new rows | D09 complete exact coverage or failure |
| Non-atomic finish-review read/launch | D02 atomic claim plus future replay marker |
| Non-idempotent Ingest/Match re-entry | D12 unique/upsert Ingest + replace-own-uncommitted Match |
| `audit.cell_name NOT NULL` for every event | D06 `event_kind` with a nullable cell name for attachments |

For full chronology, alternatives, trade-offs, evidence language, and all 93
original Decision Log rows, use `documentation/decision-history.md`.
