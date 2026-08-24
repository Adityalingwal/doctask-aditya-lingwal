# DECISIONS.md — current canonical decisions

This file answers **what is true now and why**. It is intentionally compact.
Detailed reasoning, rejected alternatives, and every superseded wording live
in this file's own Git history — `git log -p DECISIONS.md` reaches all of it,
including the append-only Decision Log this file replaced.

The task requirements are interpreted separately in
`documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`.
Do not turn our choices into brief claims.

## How to maintain this file

- Root `DECISIONS.md` contains current truth only.
- Before changing a decision, say in the entry what it replaced and on what
  date; the old wording stays in this file's Git history and is not copied
  into a second file.
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
- **Batch** — the files one run picks up that this project has never read
  before, by name or content.
- **Run** — one processing cycle for one project batch.
- **Delivery Owner** — the provider-side operator and human reviewer.

Use these words in code, tests, logs, UI, and documentation. Do not substitute
`item`, `entry`, `record`, `pile`, or `request` for the concepts above.

## Current decision index

| ID | Decision family | Status | Canonical section |
|---|---|---|---|
| D01 | Deliverable, domain, user, and run scope | Implemented and verified in slice-1 scope | Product contract |
| D02 | Human-gate scope, actions, and review queue | Implemented and verified for slice-1 gates | Human review |
| D03 | Incremental batching, watched-folder trigger, and read-once rule | Implemented and verified | Input and incremental updates |
| D04 | Formats, document types, and parsing | Mixed | Input and incremental updates |
| D05 | Register cells, statuses, attachments, citations, and the live register document | Mixed | Register and evidence |
| D06 | Audit trail and unchanged-row proof | Implemented and verified | Register and evidence |
| D07 | Pipeline stages and conditional routes | Mixed | Pipeline |
| D08 | Extract, quote location, prompt injection | Mixed | Extract |
| D09 | Match, requirement identity, and granularity | Implemented and verified in slice-1 scope | Match |
| D10 | Rules, Examine, findings, and no-findings | Implemented and verified with the scripted model | Examine and findings |
| D11 | Model provider, retry, failure classification | Mixed | Model boundary and failure handling |
| D12 | State, checkpoints, node re-entry, and Extract-call idempotency | Mixed | Reliability and concurrency |
| D13 | Run identity, statuses, lock, and queue | Implemented and verified | Reliability and concurrency |
| D14 | Database and API surface | Implemented and verified in slice-1 scope | Storage and interfaces |
| D15 | MCP and React surfaces | Implemented and verified — MCP by test and by hand; the three-column projects-and-runs screen by its front-end suite and hand-driven against the application | Storage and interfaces |
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
| Testing feedback | Label `Passed`, `Defect`, `Not found`, `Change request`, or `Unclear` from evidence |
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
| 10 | File not used, with reason | No |
| 11 | Focused incremental-update proposal | Yes |
| 12 | Final export/commit | Yes |
| 13 | Honest `No findings` result | No |

- **An empty folder makes a project and starts no run (2026-08-23).** The
  refusal, `This folder has no files. Add a document.`, lives in
  `start_or_queue_run` — the one function `POST /runs`, the MCP `start_run`
  tool and the watcher all reach, so none of the three can grow its own
  wording. The folder list carries a has-files flag so the button can say
  which of the two it is offering. Replaces the earlier "create and start
  run" step, which recorded a run that read nothing.

### Actions and persistence

- **Decision:** Every gated proposal has only **Approve** or **Reject**. The
  buttons act on the stated proposal, never resolve the underlying truth.
- **Reject:** Exclude the proposal from the register but retain it permanently
  in the run record.
- **The final-export gate is one press, not a queued question (locked
  2026-08-18).** Entering Review raises no export decision. Once every other
  decision is answered, the review is ended by one of two buttons — `Add this
  run's changes to the register` and `Discard this run's changes` — and that
  press writes the export decision, its frozen question and its answer
  together, inside the same atomic claim that takes the run out of review.
  Two buttons and not one: refusing is how a run ends without committing, and
  without it a run nobody wants would hold its project's lock for ever.
  Discarding ends the run `discarded`.
- **`finish_review` takes the answer, with no default.** `add_to_register`
  reaches both doors — `POST /runs/{id}/finish-review` and the MCP tool — and
  a call that omits it is refused with the body to send. The trade-off: the
  answer can no longer be changed between giving it and finishing, because
  the press is the decision.
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
- **A stored question is never rewritten or backfilled.** New wording applies
  to newly raised questions only, so an audit shows what each person actually
  read rather than what the system would say today.
- **What Approve and Reject will do is code's to write, never the model's
  (2026-08-17; part of the stored question since 2026-08-23).** Every kind's
  two lines are built from stored data and now sit inside the frozen text a
  person read, as `parts.if_approved` (a list of `{cell, value}`, empty where
  approving writes no cell) and `parts.if_rejected` (one sentence).
  `decisions_of_run` carries `row_number` — the register row the decision is
  about, whichever kind it is. A possible match names the cell an approved
  merge would write, worked out by `cells_a_merge_would_write`, which Commit
  reads too; an observation match names the cells of the very `pending_moves`
  entry Commit applies.
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

- **Decision:** A batch contains every file waiting when a run starts that
  this project has never read before — matched by name or by content, either
  alone is enough. A document already read, by either test, is skipped and
  never read again. See "Read-once rule" below for what "already read" means,
  and README's "What this does not do, and why" for the boundary this draws
  for a user.
- **Removed file:** Deleting a watched file does not delete its historical rows.
- **Watcher:** Poll every 2 seconds and auto-start after 5 seconds of quiet,
  provided the project has no run running, at review, or queued. Manual
  `POST /runs` remains. Files arriving during Review wait for the next run.
  Both numbers are `config/watcher.yaml`, read through `WATCHER_CONFIG_PATH`.
  **Implemented and verified** by `tests/runs/test_watched_folder.py`.
- **Baseline, not backlog:** whatever the watcher first sees in a folder is not
  an arrival, so a project created over a folder of documents starts nothing by
  itself and never surprises a fresh `docker compose up` with a paid run. The
  cost is that a restart forgets what it saw; see PROGRESS limitations.
- **Rules-only run:** When the rules a run froze differ from the ones the
  register was last examined against and no document is new, skip
  Extract/Match and run Examine against the existing register. It is the same
  run object, routed differently. **Implemented and verified** by
  `test_a_changed_rules_file_re_examines_the_register_without_reading_a_document`.
- **Unchanged-row proof:** a second run leaves every row its documents did not
  affect byte-identical — cells, citations and fingerprint. **Implemented and
  verified** by `tests/incremental/test_incremental_updates.py`. A second
  proof, `tests/incremental/test_second_run_on_corpora.py`, drove the two
  synthetic corpora and was removed with them on 2026-08-18; the guarantee
  itself is unchanged.

### Read-once rule

A document counts as already read, and is skipped, once an earlier run's
extraction of it finished with nothing left to do — either that run's changes
were added to the register (its status is `done`, tested directly since
2026-08-18: the commit node writes the rows and the status in one
transaction, so neither fact exists without the other), or the extraction
showed the document was unrelated (settled whatever its run did), or it held
no requirement and its run ended `no changes`. A no-requirement document of a
discarded or failed run is read again (decided 2026-08-18): its observations
never landed, and settling it for ever would silently lose what testing or a
handover said — the rule requirement-bearing documents already followed.
That extraction must exist
(`extraction IS NOT NULL`), so a document whose model call failed has none and
is read again next run regardless of what its name or content would otherwise
match.

- **Matched by name OR content, either alone is enough.** An edited document
  keeps its old name, so it is skipped by name; a renamed document keeps its
  old content, so it is skipped by content. Only a document new on both counts
  reaches Extract. This is the incremental-update slice's one behavioural
  change from re-reading changed files: one operator, `AND` to `OR`,
  parenthesised so it cannot swallow the extraction/status conditions around
  it.
- **Why not re-read a changed document.** Re-reading a changed file to compare
  it against the register could change an already-committed row on evidence no
  person had seen. That capability (withdrawal) never ran against a live
  model, so this phase removes it along with the re-reading that fed it,
  rather than carry an unproven capability in the riskiest part of the system.
  Superseded 2026-08-16: "Read-once rule replaces re-reading a changed
  document, and withdrawal is removed".
- **One definition, one function (2026-08-23).** The rule above is one SQL
  condition, `READ_BY_THE_PROJECT` in `app/ingest/read_once.py`, and
  `documents_read_by_project` answers "which documents of kind K has this
  project read" from it. Ingest asks it to decide whether to pay to read a file
  again; the rule gate and the absence move ask it to decide what the register
  may claim a document was silent about. A second definition let a discarded
  run's requirements document count as read for `Written down` while Ingest
  read it again — the two answers have to be one. A run's own batch counts
  where the caller passes `include_run_id`: the run's status is not `done`
  until Commit writes it, and Match, Examine and Commit have all read it by
  then.
- **Evidence/status:** Implemented and verified by change-detection tests for
  transient failure, an edited document, a renamed document, a deleted
  document, an unrelated document, and a document that asks for nothing, plus
  `test_ingest_and_match_share_one_definition_of_read`.

### D04 — formats and document types

| Concern | Current contract | Status |
|---|---|---|
| Declared formats | `.pdf`, `.md` in `config/formats.yaml` | Both readers implemented and verified |
| Unsupported format | Skip with a reason naming the two formats | Implemented and verified |
| Page limit | 20 pages in config; oversized documents skip | Implemented in `app/ingest/read_source_document.py`; binds `.pdf` only |
| PDF | `pdfplumber` extraction, `pypdf` encryption check; scanned/encrypted skip | Implemented and verified for encrypted, scanned, and oversized skips |
| Markdown | UTF-8 with Latin-1 fallback | Implemented and verified |
| Folder scan | Top-level files only, read in place | Implemented for both formats |

The two kept formats cover the two shapes a citation place can take — a
heading and a page. `.docx` and `.txt` were removed on 2026-08-17 with their
readers, tests, corpus document and dependency; superseded entry: "the
register becomes four cells".

Format is checked before type. Type is a Pydantic enum at the model boundary,
and which lists each type may fill is stated in the prompt and carried in the
generated schema:

| Document type | requirements | testing_observations | delivery_evidence |
|---|---|---|---|
| meeting notes | yes | — | — |
| client requirements document | yes | — | — |
| testing feedback | — | yes | — |
| handover summary | — | — | yes |
| unrelated | — | — | — |

The fourth type was named `related additional document` until 2026-08-17; it
is the only type allowed to fill `delivery_evidence`, so it is named after
what it is. **A batch is read in workflow order** — meeting notes → client
requirements → handover summary → testing feedback — so the document that
states an ask first is the one whose requirement creates the row and supplies
its wording. Two documents of one type fall back to file name.

`embedded_instructions` may appear on any type. A filled
list where this table says otherwise is a wrong answer: that one document is
not read, with a reason naming what came back, the batch continues, and nothing
is quietly emptied. Its buckets are:

| Bucket | Action | Status |
|---|---|---|
| Primary: meeting notes, client requirements document, testing feedback | Full declared processing | Implemented |
| Handover summary | Read, labelled and stored; never creates a register row on its own | Implemented; it reports `delivery_evidence`, which moves a row that already exists to `Handed over` |
| Unrelated | Not read, with reason | Implemented |
| Outside the enum | That document is not read, with `document type not recognised`; the run continues | Implemented |

- **Must preserve:** Accepted-format list is config; actual readers are code;
  startup warns when config names a format with no reader.
- **Damaged files are one document's problem:** a `.pdf` that no library can
  open is not read, with its reason, like an encrypted or scanned one, instead
  of ending the batch.
- **Limitation:** the page limit binds `.pdf` only, because only a paginated
  format can report a page count. Markdown, plain text and Word have none and
  none is invented for them; the shared gate in the dispatch limits any
  paginated reader added later.
- **Evidence:** `tests/documents/test_document_readers.py`,
  `tests/documents/test_supported_formats.py`,
  `tests/documents/test_document_type_buckets.py`, and one run over the
  six-document Northside Dental corpus.

## Register and evidence

### D05 — row shape

Four cells, each with its own citations:

`What was asked` · `Written down` · `What testing found` · `Status`

The register answers one question — was this asked for, and did we deliver it
— and every cell that does not serve it is weight the reader carries for
nothing. The stored column behind `Written down` is still `in_writing`.
Migration `20260817_0017` dropped the other three cells; history: 2026-08-17.

Statuses are fixed in code and in a database check constraint:

`Done` · `Partial` · `Not delivered` · `Handed over` · `Disputed` ·
`Requested` · `Excluded`

Each means one thing, written down so a model, an implementer and a reader
cannot each assume a different one:

- **`Requested`** — the ask is known, and no document read so far says anything
  about whether it was delivered or tested. Every row starts here. It makes no
  claim. **Replaced `Nothing said yet` on 2026-08-23** (migration
  `20260823_0022`; third wording, after `No evidence yet` → `Nothing said yet`
  on 2026-08-17). The cell has to be understood at a glance by a reader who has
  opened nothing else, and a status naming what *is* known does that where one
  naming a silence does not. `Not built` was rejected: no document read so far
  makes that claim.
- **`Done`** — a document reports the asked-for work exists and behaves as
  asked.
- **`Partial`** — a document reports the work exists but is wrong or
  incomplete.
- **`Not delivered`** — a document states the asked-for work is not there. This
  is a positive claim and needs a citation. It is not `Requested`:
  someone looked.
- **`Handed over`** — a handover summary reports the work exists, and testing
  has not spoken yet.
- **`Disputed`** — two documents make opposing claims about this requirement.
  The system never resolves it; it goes to a person.
- **`Excluded`** — the client's requirements document explicitly puts this
  ask outside approved scope, and the Delivery Owner approved linking that
  boundary to this row. `Written down` also reads `Excluded`, with the exact
  scope quote behind both cells. It is not a delivery or testing failure.

- What moves a row: a testing observation's label (`Passed` → `Done`,
  `Defect` → `Partial`; `Change request` and `Unclear` move no status, because
  a new ask arriving during testing is not a verdict on the work), and delivery
  evidence with no testing behind it → `Handed over`.
- A fifth testing label, **`Not found`**, carries "testing looked and the work
  is not there" — the one thing `Defect` (broken, therefore `Partial`) cannot
  say. `Not found` behind a handover claiming delivery is `Disputed`; `Not
  found` with no handover behind it is `Not delivered`, because silence
  contradicts nothing. Without this label neither status could ever be written.
- Unknown cells say what is unknown; they are never blank or guessed.
- **A cell answers in as few words as a reader can scan down a column, and the
  file behind the answer lives in the row's evidence (2026-08-23).**
  `Written down` reads `Not known yet` · `Yes` · `Excluded` · `Not mentioned`, and `What
  testing found` reads `Not known yet` · what testing said · `Not mentioned`.
  This replaces the bullet that had the cell read `Not found in <file>.` and
  the two long "Not known yet — no … has been read" sentences: a column of
  sentences is unreadable, and the same file was printed twice on every row.
  `Not mentioned` still never means "No" — the evidence behind it is the exact
  file that was read plus the sentence saying it does not mention this ask.
- **A document's silence is worked out in Match and written at Commit, by
  the absence move (2026-08-23).** `Written down` used to be composed when a
  requirement landed on a row, so a row no requirement ever landed on kept
  denying that any requirements document had been read. Now every client
  requirements document and every testing report the project has read is
  set against every row it does not mention. The result travels in
  `runs.pending_moves` beside the observations' moves, so Examine judges the
  register exactly as Commit will leave it — a rule about a silent testing
  report could never see the silence otherwise, since the cell is only
  written after the person has answered — and Commit writes that same list:
  the cell moves to `Not mentioned`, gains an absence citation, writes its
  history entry and moves the row's fingerprint.
  It only ever fills a cell still reading `Not known yet`; a cell holding `Yes`
  or a testing verdict is left exactly as it stands, and a second silent
  document behind an existing `Not mentioned` adds its evidence and nothing
  else. `Status` is never moved by an absence. One writer,
  `app/register/absence_rows.py`; a run that read such a document always
  continues to Review, because silence is a change a person approves.
- Conflicts, findings, and possible-match questions attach to rows but are not
  row cells. This preserves gate separation and cell-only fingerprints.
- **A cell keeps the citation of every document that still supports the value
  it now holds, and drops any citation supporting a value it no longer holds.**
  There is no cap on the number. `Status` is the cell this changes: the
  handover's citation stays as the row moves `Handed over` → `Done`, because
  "the work exists" is still true, while a superseded testing verdict goes,
  because it now proves something the cell denies. Every other cell holds one
  claim, so its old citation goes with its old value. This is what makes the
  one-document-per-run and paired arrival orders end with the same register.
- **Implemented and verified:** proposal/commit/register-document shape and
  six statuses, plus finding attachments, which appear on the row in the
  register document and leave its cells and fingerprint untouched. Both corpora were driven end to end in both
  arrival orders on 2026-08-17 and ended identically.

### Citations

- Present evidence = source file + usable place + exact source words.
- Absence evidence = exact file read plus explicit absence statement.
- Locator by format: PDF page, Markdown nearest heading.
- The model supplies exact words; code derives the place. Repeated words use
  the first occurrence, and the citation names that one place — the
  comma-joined list of every place left on 2026-08-23, because one source line
  (`app/ingest/source_line.py`) cannot be written from a list.
- An unfindable quote drops that requirement and records a skip reason. Plain
  normalized substring matching is intentional; no fuzzy match.
- **Evidence/status:** Markdown quote location, multi-line normalization,
  invented quote rejection, first occurrence, and Latin-1 read are verified.
  Both locators are verified by `tests/documents/test_citation_places.py`; each
  citation may only name a place its own reader produced.

### The register document, audit, and fingerprints

- **The register is read live, and the snapshot is gone (locked 2026-08-17,
  built 2026-08-18).** Commit stops copying the register into
  `runs.export_json`, and the column is dropped (migration `20260818_0021`;
  the downgrade re-adds it empty — the snapshots are not reconstructible).
  One core function builds the register document from `register_rows` at
  read time; its `exported_at` and examine section come from the newest
  `done` run, whose `finished_at` is exactly the moment the register last
  gained rows. The snapshot's one non-display reader, `collect_batch`'s
  already-read rule, tests `runs.status = 'done'` instead — semantically
  exact, because the rows and the status commit in one transaction. History:
  2026-08-18.
- **A finding reaches the register only once its run ends `done` (review
  finding, fixed 2026-08-18).** `approved_findings_of_project` also requires
  the finding's run to be `done`: an approved finding on a run still at
  review has not passed the add/discard gate, and a discarded run's finding
  never will. Before the fix the query checked only the decision, so a
  discarded run's finding could reach the display (on `main` it reached the
  next commit's snapshot the same way — the leak predated the live read).
- **The live read is one database snapshot.** `build_register_document`
  wraps its queries in a `REPEATABLE READ` transaction, so a commit landing
  mid-read cannot mix new rows with an older run's timestamp, citations or
  findings.
- JSON is the record; Markdown is generated from it. Markdown is never edited
  as a second truth.
- **The register carries no reported instruction (2026-08-17).** It is what
  the client is sent, and a note about our own reading of a document is not
  part of it. `runs.reported_instructions` stays, and the run panel's
  Reported tab still reads it from `GET /runs/{id}` — no migration was
  involved. History: 2026-08-17.
- Commit atomically writes approved rows, cell-level audit, and fingerprints.
  A fingerprint covers the four cells only, excluding attachments.
- Audit answers: which cell/attachment, before, after, run, and source.
- **Implemented:** First-run cell audit and fingerprints are written; the
  register document is verified in both formats.
- **Audit events:** `audit.event_kind` holds `cell change` or `attachment`
  (plain text plus a `CheckConstraint`, never a PostgreSQL `ENUM`).
  `cell_name` is nullable, and the cell-name check applies only to a cell
  change; an attachment must name no cell, because a finding attaches to a row
  and there is no honest cell name to write. That check still names the three
  cells `20260817_0017` dropped, because an audit entry written before that
  migration ran is history and must survive it. Migration `20260813_0005`
  backfills every existing row as a cell change; its downgrade drops
  attachment rows, which the older shape cannot represent. Proven by
  `tests/infrastructure/test_schema.py`.
- **Implemented and verified:** a second run's unaffected rows come back with
  the same cells, the same citations and the same fingerprint, compared as
  stored rather than as rendered. An approved merge moves citations onto the
  candidate row without moving its fingerprint, because a citation is not a
  cell.
- **The audit trail is readable, and it is not part of the register (locked
  and built 2026-08-18).** `read_history` (`app/register/read_history.py`) is
  one core function behind `GET /projects/{id}/history`, the `get_history`
  MCP tool and the screen's HISTORY section — read-only over `audit`, no
  migration and no change to what Commit records. It is deliberately **not**
  a key in the register document: the register says what is true now, the
  history says how it got there, and the export carries only the former.
  Entries come newest first by `created_at`, then `row_number`, then
  `cell_name` with nulls last, then the entry id — the final key added
  after review, because two findings attached to one row in one run tie
  on the first three — so one run's single-transaction writes can never
  order two ways. **A row's birth is one entry, folded in the core
  function**: Commit writes one all-null-old cell change per cell, and a
  `(run, row)` whose cell changes are all of that shape becomes a single
  `row created` entry carrying `what_was_asked` and its document — so curl,
  MCP and the screen are answered with the same list rather than each
  grouping for itself. An approved finding is its own `finding attached`
  entry, naming no cell and no document because it has neither. A project
  with no trail answers `200` and no entries, shown as `No history yet.` —
  never an error. Run numbers are computed exactly as
  `app/projects/list_projects.py` computes them, so the two surfaces cannot
  number one run differently. History: 2026-08-18.
  **Not built, deliberately:** revert or restore, register version snapshots,
  filters, search, pagination, and any history export format.

## Pipeline

### D07 — stages and routes

Full locked pipeline:

`Ingest → Extract → Match → Examine → Review → Commit`

| Stage | Job | Model call | Current status |
|---|---|---|---|
| Ingest | Read files never read before, by name or content | No | Implemented and verified for `.md` and `.pdf` |
| Extract | One document: type/requirements/testing/delivery/instructions | One per document | Implemented and verified with scripted model |
| Match | Whole batch against current register | One per batch | Implemented and verified with scripted model |
| Examine | Whole register against frozen rules | One per register | Implemented and verified with scripted model |
| Review | Present gated proposals and wait | No | Implemented and verified for slice-1 proposals |
| Commit | Atomic durable rows/audit; the register is read live afterwards | No | Implemented and verified |

All documents complete one stage before the batch moves on. Extract loops with
a per-document checkpoint. All six stages are built: Match routes to Examine
when it proposed a row and to the early exit when it did not, and Examine
always continues to Review.

Early exits are honest terminal `no changes` states with reasons:
no readable file this project has never read before; or the batch read one or
more files but traced no requirement to its own words, so nothing reached
Match. Ingest routes straight to Examine instead when no document is new but
the rules the run froze are not the ones the register was last judged
against. A batch that stated a requirement always proposes at least one row —
several requirements stating one ask land on one row, and none is dropped — so
once Match has run at all it always has something to propose; Match makes no
model call, and Extract never routes on to it, when the batch found nothing to
match.

## Extract

### D08 — one call, exact evidence, structural injection boundary

- **Decision:** One model call per document, sequentially. This makes filename
  attribution deterministic, checkpointing clean, and failures isolated.
- **Output:** type, requirements, explicit scope exclusions, testing
  observations, delivery evidence, and embedded instructions, each tied to
  exact words. A negative scope sentence from the client's requirements is a
  typed exclusion, never a positive requirement. This
  list may widen only with a real later-slice need.
- **Contract:** the model call sends `response_format` of type `json_schema`
  with `strict: true`, and the schema is **generated from the Pydantic answer
  model** (`app/model/answer_schema.py`), never hand-written a second time.
  Each field's meaning travels in the schema as its description; the prompt
  carries judgement only. Match and Examine use the same helper.
  Pydantic validation and `json_object_in` both stay regardless: the scripted
  client the test suite runs against returns plain text and knows nothing about
  `response_format`. **A schema guarantees the shape, never the truth** — a
  quote the document does not contain is still caught only by
  `app/ingest/locate_quote.py`, which is unchanged.
- **Injection:** Document text is data, never system authority. It has no code
  path to approve, commit, or export. The model may report suspicious text;
  detection is not guaranteed and no brittle phrase list is built.
- **Implemented and verified** — 2026-08-14. The proof was originally
  `tests/documents/test_document_instruction_is_reported.py`, driven against
  the intake-portal demo document that buried the hostile line; that document
  and test are deleted with the old corpora (2026-08-18 — history: "The demo
  seed is removed, and the sample corpus becomes Helpline AI"). The
  same guarantee is now proven by test fixtures that build their own document
  in a temporary folder — `tests/runs/test_reported_instructions.py` — and the
  buried-instruction fixtures elsewhere in `tests/`: the line is stored as an
  embedded instruction placed in that document and logged against the run,
  and it creates no row, changes no cell, and reaches the Delivery Owner as no
  proposed action. It **is** reported to a person on purpose — the run's own
  column, `GET /runs/{id}` and its own tab beside Skipped — because
  information nobody can see is not a report. Nothing was committed until a
  person approved it.
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
- Outcomes: new row, existing row, possible match — three, and a within-batch
  match did not add a fourth.
- **Two kinds of candidate.** A requirement matches a committed register row by
  `row_number`, or an earlier requirement of this same batch by
  `same_as_requirement_index`. One ask stated in a meeting note and again in
  the client's requirements document becomes one row carrying both citations,
  instead of two rows one of which claims the ask was never written down.
- A confident existing-row answer against a **committed** row is deliberately
  downgraded to human-reviewed possible match before evidence reaches it. A
  confident within-batch match is not: nothing in the batch is committed, and
  the run still faces the export gate. An uncertain within-batch match is still
  asked about, between the two proposed rows.
- **Open, and deliberately not built (2026-08-17).** Removing that downgrade
  was locked on 2026-08-16 on the understanding that the export gate shows such
  a merge. It does not: `GET /runs/{id}` at `needs review` carries no proposed
  row, no cell and no citation, and the register read shows committed rows
  only, so nothing shows the merge before it commits. Removing only the
  downgrade would in fact change
  nothing: `_the_candidate_to_ask_about` raises the possible-match decision
  whenever the answer names a committed row, whatever the outcome, so the
  question would still be asked and an approval would still merge. Making the
  merge automatic therefore needs the gate to show the merge first. The
  decision goes back to Aditya rather than being built around; history:
  2026-08-17.
- **A match may only point backwards**, and a chain is followed: a requirement
  may name one that created no row of its own, and the evidence lands on the
  row at the end of that chain. Pointing forward is refused, never reordered.
- The row a within-batch match lands on keeps the **earlier** requirement's
  `What was asked` and recomputes `Written down` across every requirement on
  it. The batch is read in workflow order (D04), so "earlier" means stated
  earlier in the work rather than named earlier in the alphabet.
- Every requirement index must return exactly once with a valid outcome, and
  with exactly one candidate named wherever the outcome names one. An
  incomplete answer fails the run; it never defaults to a guess.
- The three outcome words are a `Literal` on both answer models, so the
  generated schema refuses an invented outcome before the reply is read.
- **The backend builds every decision sentence; the model writes none
  (2026-08-23).** Replaces "Match writes the question a person reads, and it is
  stored unchanged" (2026-08-17), which is why: a model-phrased sentence
  brought `\"` escapes and `Row #8` onto the screen, and a template cannot.
  `question` leaves `MatchOutcome`, the observation outcome model and
  `MatchSettlement`, with the refusals that failed a run on a missing one.
  `app/review/decision_text.py` builds all three shapes from the candidate
  row's own cells, this batch's own quote and the move an approval would make
  — worked out by `cells_a_merge_would_write`, the one rule Commit's merge
  also reads, so the line never promises a change Commit will not write.
  `decisions.question` still freezes the whole text at raise time, and
  `decisions.parts` freezes the same text taken apart so a screen can lay it
  out without composing wording of its own. Two observations on one row are
  one decision carrying two quote blocks, never a stitched paragraph. A
  candidate this same run proposed reads `Row N (proposed by this run)`.
- Each requirement reaches the Match prompt with its `document_type`, taken
  from the stored extraction and never guessed from a file name, so the
  question can name the kind of document each statement came from.
- **Explicit scope exclusions never create rows (2026-08-25).** Match treats
  one as a statement about already-requested work: no related row leaves it
  `not attached`; a proposed link always goes to the Delivery Owner, even for
  a row proposed in the same batch. Approval moves `Written down` and `Status`
  to `Excluded` with the exact quote; rejection leaves the row unchanged and
  retains the proposal on the run. This implements conflict surfacing without
  making negative wording into work the provider is expected to deliver.
- Approved merge moves citations to the candidate — following a merge already
  approved, since two proposals of one batch can settle in either order — and
  marks the proposal with `merged_into_register_row_id`; it is retained and
  skipped by Commit. Reject keeps it as a separate proposed row. Row-number
  gaps are accepted. **Every marker is left pointing at the row that holds the
  evidence**, so a marker is never two hops from it: readers of that column
  follow it exactly once, and a two-hop chain would report a finding against a
  row Commit never commits.
- **An approved merge brings the surviving row's cells up to the evidence it
  just gained**, which reverses the slice-1 rule that a merge moved citations
  and never a cell. Only the cell the arriving requirement can speak to
  moves: `Written down`, which otherwise keeps denying a requirements document
  the row now cites. It holds one claim, so its old citation goes with its old
  value. On an
  already-committed row this writes the before-and-after audit entry and moves
  the fingerprint, exactly as an approved move does — a changed cell that left
  the fingerprint still would be the register lying about itself. History:
  2026-08-16.
- **Evidence/status:** Implemented and verified by coverage, duplicate-index,
  missing-candidate, merge, rejection, and node-rerun tests, by ten
  within-batch tests in `tests/match/test_within_batch_duplicates.py`, and by
  both corpora driven first-run end to end.
- **Open:** pgvector retrieval is unnecessary for current short documents; if
  still unused at submission, disclose the defended stack choice.

## Examine and findings

### D10 — rules and findings

- Rules live in user-editable `config/rules.yaml`; adding or changing a rule is
  a data change, and there is no other way in. Shipped R1, R2, R4 and R5 cover
  written requirement, change request versus bug, missing testing outcome, and
  `Done` without a testing outcome.
- **No rule is judged outside `config/rules.yaml` (2026-08-17).** The two
  deliverable checks that lived in code are gone: D1 was deleted, because
  `commit_register` already refuses to commit a row carrying no citation, and
  D2 moved into the rules file as `R5`. `R3`, the only rule that needed a
  document date, left with the date cells. Ids are not renumbered — a finding
  stores the id it was raised under. What is given up: a code check always
  runs, while a model-judged rule depends on the model.
- One findings table, no rules table. Each finding freezes rule id and text,
  found issue, evidence, row, and the whole question the backend built; its
  answer is read from the decision it names (D02), not stored again. The
  history line names the rule by its text alone (`Row 1 · Finding: <text>`).
- **A finding is four fields, and only its issue line is the model's
  (2026-08-23).** Replaces "A finding is five fields, and Examine writes the
  question itself" (2026-08-17), for the D09 reason: a model-phrased question
  put JSON escapes and a stale row number in front of a person. The model
  answers `rule_id`, `row_number`, `issue` and `evidence`; `question` leaves
  the model. The issue line stays the model's because only the rule can say
  what breaking it looks like, and the backend wraps it — the row block, the
  rule's own words, the issue, `Does row N break this rule?`, and what each
  answer does — and stores the whole as `decisions.question`. An empty issue
  or evidence is still refused.
- **The change-request rule is a declared limitation, not extended
  (2026-08-23).** A testing observation that attached to no row reaches the
  person through the Skipped tab, and no rule runs on it — Examine sees
  register rows only. Written out once, in README "What it does not do".
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
- **Who computes what:** every applicable rule is judged by the model in one
  Examine call. An unusable rules file fails the run at the boundary and is
  never read as "no rules".
- **A rule waits for the documents it is about (`applies_when`, 2026-08-23).**
  Each rule in `config/rules.yaml` may name the document kinds it needs, from
  the four Extract reports, and runs only once the project has read every kind
  it names (the read-once definition above). This **replaces the 2026-08-17
  lock "every rule is judged by the model in one Examine call"** — unqualified.
  Why: the testing-outcome rule, judged before any testing feedback existed,
  raised findings against silence — six of them in one demo. A rule naming no
  kind applies always, which is what a test's own rules file relies on.
  Validation lives in `load_rules`, so a value outside the four stops the
  application at startup and again at every freeze, naming all four.
- **`runs.rules_applied` (JSONB, 2026-08-23)** names exactly the rules Examine
  sent to the model, written in the same statement as `examined_row_count`, and
  null until Examine has run. `rules_snapshot` is unchanged and stays the
  fingerprint source: a snapshot holding only the applied subset would move the
  fingerprint every run and trigger rules-only re-examines that changed
  nothing. Every reader of "which rules ran" — `examine.rules`, the Markdown
  export, and the register read below — comes from this column.
- **An approved finding stays until the same rule and row receive a newer
  explicit decision (2026-08-25).** This replaces the 2026-08-23 latest-run-
  per-rule projection. A later model call that applies a rule but raises
  nothing is silence, not a human decision, and cannot erase an approved
  finding. A newer approved finding for the same rule and row replaces the one
  the register shows; a newer rejected one clears it. The same rule on another
  row is independent. No schema change and no destructive resolution flag:
  every finding and decision remains in History, while the register reads the
  latest explicit decision for each `(rule_id, register_row_id)` pair. Why:
  the documented Helpline flow approved R1 on row 7, but a later model call
  did not repeat it and the register silently hid a gap the Delivery Owner had
  approved. Human decisions outrank absence from a later model answer.
- **`examined_row_count` on `runs`** records how many rows Examine judged, so
  the `No findings` result can state it after the run ends, whether or not
  the run committed. A proposal still waiting on a possible-match answer is
  **not** one of them (2026-08-23): Examine assumes the match, judges the row
  it would join with the proposal's `Written down` overlaid, and counts real
  rows only. **Known limitation:** if the person then rejects the match, the
  new row gets no finding in that run; the next run raises it.
- **Known limitation:** a rule is judged by a model, so a later run may not
  repeat a finding. The approved finding remains on the register until the
  same rule and row produce another finding that a person decides.
- **Status:** Implemented and verified with the scripted model. Findings reach
  the human gate through the existing review queue, a rejected finding stays in
  the run record and never reaches the register, and Examine re-entry after a
  crash replaces this run's unanswered findings rather than adding to them.
  Proven by `tests/examine/test_examine_findings.py`,
  `tests/examine/test_rules_apply_when_their_documents_are_read.py`,
  `tests/examine/test_an_unanswered_possible_match_is_examined_as_the_match.py`,
  `tests/register/test_the_register_shows_the_latest_finding.py`,
  `tests/examine/test_examine_answer.py`,
  `tests/examine/test_frozen_rules.py`,
  `tests/examine/test_rules_live_only_in_config.py`, and
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
  returns one `queued` run; its batch is formed only when it starts. Different
  projects may run concurrently.
- Slice 1 executes background work inside one FastAPI process. A separate
  worker is a legitimate later change; database locks preserve correctness.
- **Run statuses, renamed 2026-08-15 so the screen can print the stored value
  verbatim, and `export rejected` renamed to `discarded` 2026-08-18
  (migration `20260817_0019`):** `queued`, `running`, `needs review`, `done`,
  `discarded`, `failed`, `no changes`.
- `done` means the run's changes were added to the register. `discarded`
  means the Delivery Owner pressed
  `Discard this run's changes`, so nothing was committed. `failed` is
  deliberate unrecoverable stop. Early exits use `no changes` plus a reason.
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
  - A second run on one project is `queued`, however often it is asked for,
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

- **`decisions.parts` (JSONB, nullable, 2026-08-23)** — the whole decision
  text taken apart, frozen beside `question` at raise time. Nullable because
  the export gate is a button, not a card, and has no parts at all.
- **`get_register` rows carry `evidence` (2026-08-23)** — citations merged by
  quote, each entry naming its source line, its words and the cells it
  supports; an absence carries its sentence and no quote. **The per-row
  `citations` list and the run-level `examine` block left the register JSON on
  2026-08-24** (they were kept beside `evidence` only until the screen read the
  new fields): a row's findings are the row's own `findings` key, absent
  entirely on a clean row, and which rules last judged the register is the
  top-level `rules`. The run payload's own `examine` block is untouched — it is
  what one run judged and found, which is a different question.

Eight slice-1 API endpoints:

| Endpoint | Job |
|---|---|
| `POST /projects` | Get-or-create the one project for a source folder (§ folder identity below); no name field |
| `GET /projects` | Every project, each with its runs nested, in one answer (L1) — the folders `POST /projects` may point at ride along too |
| `POST /runs` | Start/queue run by project id; return immediately |
| `GET /runs/{id}` | Durable status, stage, what the run did not use, failure, decisions |
| `POST /runs/{id}/decisions` | Answer one decision UUID |
| `POST /runs/{id}/finish-review` | Validate/claim review completion |
| `GET /projects/{project_id}/register` | The project's register, live from its committed rows, JSON or Markdown |
| `GET /projects/{project_id}/history` | The project's register history, read from `audit`: what changed, when, and from which document (§ history read below); JSON only |

**The list of what a run did not use is called `skipped`, in all three places
(locked 2026-08-23, replacing `not_used` of 2026-08-17, which had itself
replaced `skipped`).** Why the name went back: `not_used` was chosen because
"skipped" read wrongly for a quote out of a file that *was* read, and the kind
words answer that objection directly, so one word can carry the whole list
again. The column is `runs.skipped` (migration `20260823_0024`, `ALTER TABLE
... RENAME COLUMN`, downgrade the exact reverse; migration `20260818_0020`,
which did the opposite rename, is left alone); the payload field both doors
answer with is `skipped`. Every entry carries one of exactly three kinds,
named once in `app/runs/skipped_kinds.py`: `read before` (an earlier finished
run read this file, by name or content), `not read` (unrelated, too long,
encrypted, wrong format, unknown document type, failed model call — every
reason a file was never read), and `not attached` (something a document said
that reached no register row). A `not attached` entry keeps its `summary` and
carries a `source_line` where the words were located in the file, and `null`
where they were never in it — a silence has no place to point at, and its
reason names the file instead. Every sentence in the list is the backend's;
the screen prints `<file> — <reason>` and writes nothing of its own.

`GET /runs` (every run, flat, newest first) is replaced by `GET /projects`,
not kept beside it — two list shapes for the same data was exactly the drift
this repository's conventions forbid. Superseded wording: "The screen becomes
projects, and inside each project its runs."

**A folder is a project's identity (locked 2026-08-16, superseding the demo
seed's own "is `projects` empty" check and the claim that `projects.name`
carries no unique constraint — history: "A folder is a project, and the
register moves to the project").** `source_folder_path` is unique
(`uq_projects_source_folder_path`, migration `20260815_0013`), and
`create_project` (`app/projects/create_project.py`) is get-or-create: two
calls for one folder return the same project id, `created: false` the
second time; a `UniqueViolation` from a concurrent creator is caught and
re-read rather than failed. A project's name is derived from its folder
(`intake-portal` → `Intake Portal`) and is **never accepted from a
caller** — no `name` parameter, field, or MCP argument anywhere. There is no
rename. `source_folder_path` is confined to `config/projects.yaml`'s
configured root: an absolute path or one containing `..` is refused
outright, and what remains must resolve directly inside the root, not the
root itself and not nested two levels down — closing a real hole (a folder
pointed at the repository root would have read `README.md`/`TASK.md`/
`DECISIONS.md` as client documents, reachable from curl and MCP before this
change). The folder is stored as the one path it resolves to, never as the string a
caller typed: `sample-projects/x`, `sample-projects/./x` and
`sample-projects/x/` name one directory, and stored raw they would be three
projects over it, each with its own register, lock and watcher. For the same
reason `projects_root` itself must be a relative folder inside the repository
— an absolute root is refused where the file is read, because the dropdown
offers `<root>/<folder>` while creation refuses every absolute path, and the
two must not be configurable into disagreeing. **No project is seeded at
startup (2026-08-18, superseding the demo seed — history: "The demo seed is
removed, and the sample corpus becomes Helpline AI")**: `sample-projects/`
starts empty, and a project
exists only once an operator creates one by hand, through `POST /projects` or
the MCP `create_project` tool; get-or-create alone still makes a restart
safe. A `POST /projects` that created nothing answers `200`, not `201`.
**Implemented and verified** in slice-1
scope. **Limitation:** confinement is checked when a project is created, not
again when its folder is later read; nothing but `create_project` writes that
column, so no unconfined path can reach the database, but a folder replaced by
a symlink after creation is not re-checked.

### D15 — MCP and React

- MCP mirrors the eight endpoints 1:1: `create_project`, `list_projects`,
  `start_run`, `get_run_status`, `submit_decision`, `finish_review`,
  `get_register`, `get_history`. `finish_review` takes `run_id` and `add_to_register` — yes
  adds this run's changes to the register, no discards them — the same
  argument the endpoint takes, into the same core function.
- It mounts in the FastAPI process at `/mcp` and calls the same core functions
  the endpoints call. Existence checks, refusals and the shape a caller is told
  live in core, so a door decides only how to carry a refusal, never what it
  says: `UnknownId`, `NotPossibleNow`, `UnusableRequest`, `RunsUnavailable`
  and `ProjectsUnavailable` become 404, 409, 400, 503 and 503 over HTTP and
  reach a tool caller as the same sentence.
- The dependency is the official `mcp` SDK pinned at `1.29.0`. Its 2.x line was
  days old and changes the HTTP stack it depends on; `fastmcp` would put a
  second server framework beside FastAPI.
- **The screen is three columns (L1–L10, locked 2026-08-15, superseding the
  single run list):** projects (16rem), one selected project's runs (12rem,
  collapsible to a strip that
  keeps the open run's number visible), and the open run's detail, read one
  at a time behind tabs. One question component serves every gate; it
  branches only on a `finding`, which is shown as rule, row and evidence
  rather than as one sentence.
- A project card shows a status mark (`●` running, pulsing; `◍` at review,
  still; `○` nothing live — never the card or the stage row), its run count,
  its most recent run's date, and — only while live — the active run's stage
  strip or its waiting-decision count. A card never shows a folder path; the
  path is shown in exactly one place, the Add-project box, while a folder is
  being chosen. A project can hold at most one `running`/`needs review` run
  (the partial unique index), so the card never sums waiting decisions across
  runs, and a failed or superseded run's leftover unanswered decisions are
  never counted anywhere — `app/review/submit_decision.py` refuses an answer
  on a run that is not at review.
- Section tabs still carry `role="tab"`, not the button role, because
  choosing what to read is navigation — the only actions on a run stay
  Approve, Reject and the two buttons that end the review. **A run panel has
  three tabs — Run, Skipped, Reported instructions (locked 2026-08-23,
  replacing Stages / Not used / Decisions of 2026-08-16, which had itself
  superseded a fourth Register tab — see the register bullet below).** Why:
  the stages, what the run is waiting for and the questions it raised were
  three tabs describing one run, and a reader had to visit all three to learn
  whether anything was wanted of them. They are now one Run tab, read top to
  bottom — stages, why it ended early, the waiting block, the decisions, the
  rules. A tab wears a count only when it counts something above zero.
- **A skipped entry's label comes from its `kind` and from nothing else**
  (locked 2026-08-17): the screen maps `read before`, `not read` and
  `not attached` to `Read before`, `Not read` and `Not attached to any row`,
  and an entry whose kind it does not recognise renders with no label at all. There is no default
  label anywhere — a wrong label is worse than none, and the server may learn
  a kind before the screen does.
- **The stage strip's own stage wins over "done" only while the run is active**
  (`running` or `needs review`). Extract writes its finished mark after
  every document, not just the last one, so a batch's own stage can read
  "finished" before the batch is done; the run's current stage overrides that
  reading while the run is still working, but a `done`, `failed`, or otherwise
  terminal run shows its last stage as `done`, not stuck "working" forever.
- **A project is created, and its first run started, from `AddProject.jsx`**
  (superseding the `StartRun` form): a box the `Add project +` button at the
  bottom of the projects column opens, in every state — empty or not, no
  inline first-time form. **There is no name field (locked 2026-08-16,
  superseding the folder-then-name paragraph and its empty-name check — see
  D14's folder-identity bullet).** The box chooses only a folder — a dropdown
  of what `config/projects.yaml`'s configured root holds on disk, filtered to
  folders that do not already carry a project, never invented and never
  created by the system; when nothing is left the dropdown stays where it
  is, disabled, its one option reading "No folder left to add." instead of
  "Choose a folder." Its own check is only that a folder is chosen ("Choose
  the folder to watch."); every other rule, including whether the folder
  exists, stays the server's, shown unchanged under "Could not create this
  project", never "the server refused". A retry after a failed `POST /runs`
  never repeats `POST /projects` — held client-side via the returned
  `project_id`, belt-and-suspenders now that `source_folder_path` also
  carries a real unique constraint (D14) — and the button stays disabled
  through the parent's re-read. This box does not disappear once a run
  exists: a second, third, or later project is created from the same
  button the first one was.
- **A register row's evidence is read in a panel, not under the table (locked
  2026-08-23, superseding the per-row Evidence list beneath the register).**
  The list repeated every quote of every row down one page, so the table a
  reader came for scrolled away. Clicking a row opens a panel over a dimmed
  backdrop; the table does not move, and ×, Escape and a click outside all
  close it. `useState` only — no router and no dialog library.
- **The address carries both ids (locked 2026-08-23).** `?project=<id>` alone
  selects that project and opens its newest run; `?project=<id>&run=<id>` opens
  that run; `?run=<id>` alone still works, because the run's own answer names
  its project. It is written by one effect from what is on screen rather than
  by each click, so a link can never name something the panel is not showing.
  Reloading therefore keeps the reader where they were, which is why no
  separate "remember the last project" mechanism exists.
- No blanket approve tool, waiting wrapper, separate MCP logic, state library,
  design system, dashboard, settings, or charts.
- **The screen polls `GET /projects` and `GET /runs/{id}` unconditionally, on
  the same fixed interval (`ui/config/screen.json`), whatever is on screen
  and whatever a run's status is (L1, locked 2026-08-15).** There is no
  per-project runs endpoint and no conditional refresh: at this size the
  payload is a few kilobytes, and one unconditional read is easier to reason
  about than conditional refresh rules. `GET /projects/{id}/register` is
  read on the same interval while the register panel is open. Nothing a
  person clicked is shown: an
  answer is posted and the screen then re-reads the run it was recorded
  against.
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
  React is **implemented**; the projects-and-runs screen (2026-08-15) passes
  its front-end suite and is hand-verified against the application — see
  `PROGRESS.md` for the driven scenarios and what each showed. Layout and
  visual treatment are no longer open. Answering one decision at a time is
  locked in D02, and the screen must not offer any approve-all or
  batch-submit affordance.
- `GET /projects` and `list_projects` are built, both calling
  `app/projects/list_projects.py`'s one core function: every project, run
  count, most recent run date, and its runs nested (id, run number within
  the project, status, `started_at` — `null` for a run that has not started,
  never substituted with `created_at` — stage, waiting-decision count,
  finished stages, and — on a `done` run — the project's committed row
  count, read live from `register_rows`), plus the projects root and
  the folders inside it, no cap on any list.
- **The register is the project's own panel, not a run's tab (locked
  2026-08-16, superseding the register-tab limitation below — history: "A
  folder is a project, and the register moves to the project").**
  `register_rows` was already keyed by `project_id` with `is_committed`, one
  register per project accumulating across runs; only the screen's
  presentation contradicted that. A `Register` entry sits above a project's
  runs in the middle column (`ui/src/RunColumn.jsx`), showing the project's
  committed row count once any run has committed; opening it shows the
  register in the right panel — the same panel a run opens into, reusing
  `ui/src/Register.jsx` unchanged — and clears whatever run was open and
  both refusals, the same clearing rule `openRun` already follows. **The
  panel reads the register route directly (2026-08-18, superseding the
  walk over the project's runs and the run-level export read):** one GET of
  `GET /projects/{id}/register`, no run in between. While the project holds
  no committed row the server answers the register with no rows and the
  panel reads exactly "Nothing has been added to this register yet." —
  never an empty table and never an error.
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
  `rates_usd_per_token` in `config/model.yaml` are all gone.
- **What replaced it: `runs.finished_stages`.** A jsonb object keyed by stage
  name only (`{"ingest": true, "extract": true, ...}`), written where each
  stage's pass ends with the same `||` merge the dropped `stage_timings` used,
  so a node that re-enters after a kill (D12) overwrites its own key instead
  of adding a second one. `read_run_status` and `GET /projects`/`list_projects`
  both report it as an ordered list of stage names
  (`app/runs/finished_stages.py:ordered_finished_stages`), never the keyed
  object and never the keys unordered.
- **Why not derive it from `runs.stage` instead:** on the rules-only route
  Ingest goes straight to Examine, so Extract and Match never execute; reading
  the answer off `runs.stage` alone would call them finished the moment the
  run reached a later stage. `finished_stages` records only what actually ran.
- **The run logger owns its stdout handler (2026-08-18).**
  `configure_run_logging` attaches it once at startup, at INFO, with
  propagation off so no host root handler prints an event twice. Without it
  Python prints nothing below WARNING, so the promised JSON lines never
  reached `docker compose logs`.
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
  document-type enum and its buckets, and per-format citation places. The two
  synthetic corpora that exercised it were removed 2026-08-18 for the
  Helpline AI corpus.
- The rules and findings slice is built: Examine, the `findings` table, rules
  frozen per run, and the attachment audit event. Every rule lives in
  `config/rules.yaml`.
- The MCP slice is built: its six tools mounted in the same process over the
  same core functions the endpoints call.
- The incremental update slice is built: the watched folder, the read-once
  rule keyed by name or content, the rules-only route, and the byte-identical
  unchanged-row proof, carried today by
  `tests/incremental/test_incremental_updates.py`. It added no tool.
- The reliability slice is built, and it is proof rather than construction: the
  concurrency and injection tests were written against the lock, the queue and
  the Extract path exactly as the earlier slices left them, and none of them
  needed a line of that code changed.
- The operations slice was built and then cut back: its timing and cost are
  dropped (D16), leaving structured run logging as what it contributed.
- `runs.finished_stages` replaced what the dropped timings were being read
  for. The seventh surface on both doors was `GET /runs`/`list_runs`, then
  `GET /projects`/`list_projects` replaced it in place (2026-08-15) once the
  screen became projects, and inside each project its runs. Every planned
  slice is now built; what remains is the open fresh-clone and image-only
  verification and the first live-model run.

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
| 8 | No document authority | Hostile document cannot approve/commit/export | Verified by test fixtures that build their own buried-instruction document (D08) |
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
   on 2026-08-14 with the run list and the Tailwind tokens, and resettled
   2026-08-15 into the three-column projects-and-runs shape (D15) — item 5
   below is resolved by it.
3. Whether real document sizes justify pgvector retrieval or Extract fan-out.
4. Exact later-slice storage choices where this file explicitly leaves them
   open; do not invent them before their slice.

## Known limitations and unverified assumptions

- No live model call has run; provider quality, exception shapes, latency, and
  cost are unverified.
- Register-size and short-document assumptions remain unmeasured on a full
  corpus; no live-model run has exercised one yet.
- The page limit binds `.pdf` only; no other declared format reports pages.
- A handover summary that lists requirements, in a run that never ends
  `done`, is read again by the next run.
- Rules about elapsed time cannot be judged: the register keeps no document
  dates.
- Work stopped by something outside the provider's control is reported through
  the source document, not through a cell of its own.
- A batch holding two documents of one type orders them by file name.
- One Extract call can repeat in the answer-to-checkpoint kill window.
- A rejected finding clears the register for that rule and row. A later model
  call may raise a new finding there, which requires a new human decision.
- Files arriving during Review wait; the project lock may be held a long time.
- Oversized PDFs are not read rather than chunked, and scanned PDFs are not
  read rather than OCR'd; chunking and OCR are not planned for V1.
- Timing and cost are dropped (D16). Nothing reports a duration, a token count
  or a cost; which stages a run finished is read from `runs.finished_stages`.
- The review screen is built by Node, which the application image does not
  carry, so `ui/dist` must be built before the screen can be served.
- The watcher holds what it last saw in memory, so a restart re-baselines every
  folder and a file that arrived while the application was down starts no run
  of its own.
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
| Known/related-unknown/unrelated | D04 primary/handover summary/unrelated |
| Software feature delivery/customer/dev team | D01 Software Requirements-to-Delivery/Client/Software Provider |
| Feature request list primary type | D04 client requirements document |
| Blocker as document type/undecided representation | D01 condition; the source document reports it, and no cell does |
| One run equals one project | D01 project context + document-batch run |
| Manual-only run trigger | D03 auto-start watcher plus manual endpoint |
| Five register statuses; the seven-cell row | D05 four cells and six statuses including `Handed over` |
| Location always derived without caveat | D05/D08 exact-word locator with repeated-word limitation |
| Empty-input Ingest always ends | D03/D07 rules-only route to Examine |
| Five/six API endpoints; flat `GET /runs` run list | D14 eight endpoints including `GET /projects`, every project with its runs nested |
| `done` as generic terminal state | D13 honest `failed`/`no changes`/`discarded` |
| Status-only already-read check | D03 extraction + export/unrelated/no-requirement rule |
| Already-read matched by name AND content; requirement withdrawal | D03 read-once rule matched by name OR content; withdrawal removed |
| Unmarked emptied merge proposal | D09 `merged_into_register_row_id` |
| Missing Match outcomes default to new rows | D09 complete exact coverage or failure |
| Non-atomic finish-review read/launch | D02 atomic claim plus future replay marker |
| Non-idempotent Ingest/Match re-entry | D12 unique/upsert Ingest + replace-own-uncommitted Match |
| `audit.cell_name NOT NULL` for every event | D06 `event_kind` with a nullable cell name for attachments |
| Code-composed review questions in `propose_rows`, `move_rows`, `found_issue` | D09/D10 the model writes the sentence and it is stored unchanged |
| The export carrying `reported_instructions` | D05 the run payload and the Reported tab carry it; the register does not |
| Run-level export snapshot (`runs.export_json`, `GET /runs/{id}/export`, `get_export`, the 409-before-commit contract) | D05/D14/D15 the register is read live from `register_rows` through `GET /projects/{project_id}/register` and `get_register` |

For the full chronology, the alternatives, the trade-offs and all 93 original
Decision Log rows, read this file's Git history: `git log -p DECISIONS.md`.
