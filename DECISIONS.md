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
| 10 | File skipped with reason | No |
| 11 | Focused incremental-update proposal | Yes |
| 12 | Final export/commit | Yes |
| 13 | Honest `No findings` result | No |

### Actions and persistence

- **Decision:** Every gated proposal has only **Approve** or **Reject**. The
  buttons act on the stated proposal, never resolve the underlying truth.
- **Reject:** Exclude the proposal from the register but retain it permanently
  in the run record. Only rejecting final export ends `export rejected`.
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
  (2026-08-17).** It is fixed text per kind, printed beside values the server
  computed, and it is never part of the stored question. `decisions_of_run`
  carries `row_number` — the register row the decision is about, whichever
  kind it is — and `moved_cells`, read from the very `pending_moves` entry
  Commit applies. A possible match shows only the shape (`one row` /
  `a separate row`), because the new `Written down?` is worked out inside
  Commit; an observation match shows the values, because they were stored
  before the question was raised.
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
  register was last examined against and no document is new, skip
  Extract/Match and run Examine against the existing register. It is the same
  run object, routed differently. **Implemented and verified** by
  `test_a_changed_rules_file_re_examines_the_register_without_reading_a_document`.
- **Unchanged-row proof:** a second run leaves every row its documents did not
  affect byte-identical — cells, citations and fingerprint. **Implemented and
  verified** on both synthetic corpora by
  `tests/incremental/test_second_run_on_corpora.py` and
  `tests/incremental/test_incremental_updates.py`.

### Read-once rule

A document counts as already read, and is skipped, once an earlier run's
extraction of it finished with nothing left to do — either that run exported a
register, or the extraction showed the document was unrelated or held no
requirement the register could take. That extraction must exist
(`extraction IS NOT NULL`), so a document whose model call failed has none and
is read again next run regardless of what its name or content would otherwise
match.

- **Matched by name OR content, either alone is enough.** An edited document
  keeps its old name, so it is skipped by name; a renamed document keeps its
  old content, so it is skipped by content. Only a document new on both counts
  reaches Extract. This is the incremental-update slice's one behavioural
  change from re-reading changed files: one operator, `AND` to `OR`,
  parenthesised so it cannot swallow the extraction/export conditions around
  it.
- **Why not re-read a changed document.** Re-reading a changed file to compare
  it against the register could change an already-committed row on evidence no
  person had seen. That capability (withdrawal) never ran against a live
  model, so this phase removes it along with the re-reading that fed it,
  rather than carry an unproven capability in the riskiest part of the system.
  See `documentation/decision-history.md`, "Read-once rule replaces re-reading
  a changed document, and withdrawal is removed".
- **Evidence/status:** Implemented and verified by change-detection tests for
  transient failure, an edited document, a renamed document, a deleted
  document, an unrelated document, and a document that asks for nothing.

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
readers, tests, corpus document and dependency; history:
`documentation/decision-history.md`, "the register becomes four cells".

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
skipped with a reason naming what came back, the batch continues, and nothing
is quietly emptied. Its buckets are:

| Bucket | Action | Status |
|---|---|---|
| Primary: meeting notes, client requirements document, testing feedback | Full declared processing | Implemented |
| Handover summary | Read, labelled and stored; never creates a register row on its own | Implemented; it reports `delivery_evidence`, which moves a row that already exists to `Handed over` |
| Unrelated | Skip with reason | Implemented |
| Outside the enum | Skip that document with `document type not recognised`; the run continues | Implemented |

- **Must preserve:** Accepted-format list is config; actual readers are code;
  startup warns when config names a format with no reader.
- **Damaged files are one document's problem:** a `.pdf` that no library can
  open is skipped with its reason, like an encrypted or scanned one, instead of
  ending the batch.
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

`What was asked` · `Written down?` · `What testing found` · `Status`

The register answers one question — was this asked for, and did we deliver it
— and every cell that does not serve it is weight the reader carries for
nothing. The stored column behind `Written down?` is still `in_writing`.
Migration `20260817_0017` dropped the other three cells, and `20260817_0018`
renamed `No evidence yet` to `Nothing said yet` so it stops reading as the
sibling of its opposite `Not delivered`; history:
`documentation/decision-history.md`, 2026-08-17.

Statuses are fixed in code and in a database check constraint:

`Done` · `Partial` · `Not delivered` · `Handed over` · `Disputed` ·
`Nothing said yet`

Each means one thing, written down so a model, an implementer and a reader
cannot each assume a different one:

- **`Nothing said yet`** — no document read so far says anything about whether
  this was delivered or tested. Every row starts here. It makes no claim.
- **`Done`** — a document reports the asked-for work exists and behaves as
  asked.
- **`Partial`** — a document reports the work exists but is wrong or
  incomplete.
- **`Not delivered`** — a document states the asked-for work is not there. This
  is a positive claim and needs a citation. It is not `Nothing said yet`:
  someone looked.
- **`Handed over`** — a handover summary reports the work exists, and testing
  has not spoken yet.
- **`Disputed`** — two documents make opposing claims about this requirement.
  The system never resolves it; it goes to a person.

- What moves a row: a testing observation's label (`Passed` → `Done`,
  `Defect` → `Partial`; `Change request` and `Unclear` move no status, because
  a new ask arriving during testing is not a verdict on the work), and delivery
  evidence with no testing behind it → `Handed over`.
- A fifth testing label, **`Not found`**, carries "testing looked and the work
  is not there" — the one thing `Defect` (broken, therefore `Partial`) cannot
  say. `Not found` behind a handover claiming delivery is `Disputed`; `Not
  found` with no handover behind it is `Not delivered`, because silence
  contradicts nothing. Without this label neither status could ever be written.
- Unknown cells say why they are unknown; they are never blank or guessed.
- **`Written down?` is answered against every client requirements document the
  *project* has read**, not this run's batch. A document is read once for a
  project's whole life, so a run-scoped answer would put "no client
  requirements document has been read" back on every row a later run proposes.
  Once one has been read and does not mention the ask the cell reads
  `Not found in <file>.`, never "No" — a document saying nothing about an ask
  cannot support that claim.
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
- **Implemented and verified:** proposal/commit/export shape and six statuses,
  plus finding attachments, which appear on the row in the export and leave its
  cells and fingerprint untouched. Both corpora were driven end to end in both
  arrival orders on 2026-08-17 and ended identically.

### Citations

- Present evidence = source file + usable place + exact source words.
- Absence evidence = exact file read plus explicit absence statement.
- Locator by format: PDF page, Markdown nearest heading.
- The model supplies exact words; code derives the place. Repeated words use
  the first occurrence.
- An unfindable quote drops that requirement and records a skip reason. Plain
  normalized substring matching is intentional; no fuzzy match.
- **Evidence/status:** Markdown quote location, multi-line normalization,
  invented quote rejection, first occurrence, and Latin-1 read are verified.
  Both locators are verified by `tests/documents/test_citation_places.py`; each
  citation may only name a place its own reader produced.

### Export, audit, and fingerprints

- JSON is the record; Markdown is generated from it. Markdown is never edited
  as a second truth.
- **The export carries no reported instruction (2026-08-17).** It is the
  register the client is sent, and a note about our own reading of a document
  is not part of it. `runs.reported_instructions` stays, and the run panel's
  Reported tab still reads it from `GET /runs/{id}` — no migration was
  involved. History: `documentation/decision-history.md`, 2026-08-17.
- Commit atomically writes approved rows, cell-level audit, fingerprints, and
  export. A fingerprint covers the four cells only, excluding attachments.
- Audit answers: which cell/attachment, before, after, run, and source.
- **Implemented:** First-run cell audit and fingerprints are written; JSON and
  Markdown exports are verified.
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
| Commit | Atomic durable rows/audit/export | No | Implemented and verified |

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
- **Output:** type, date, requirements, testing observations, delivery
  evidence, blockers, and embedded instructions, each tied to exact words. This
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
- **Implemented and verified** — 2026-08-14, by
  `tests/documents/test_document_instruction_is_reported.py`, which drives the
  demo document that buries the hostile line through a real run: the line is
  stored as an embedded instruction placed in that document and logged against
  the run, and it creates no row, changes no cell, and reaches the Delivery
  Owner as no proposed action. It **is** reported to a person on purpose — the
  run's own column, `GET /runs/{id}`, both exports and a fourth tab beside
  Skipped — because information nobody can see is not a report. The export was
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
  row, no cell and no citation, and `GET /runs/{id}/export` answers `409` until
  the run has committed. Removing only the downgrade would in fact change
  nothing: `_the_candidate_to_ask_about` raises the possible-match decision
  whenever the answer names a committed row, whatever the outcome, so the
  question would still be asked and an approval would still merge. Making the
  merge automatic therefore needs the gate to show the merge first. The
  decision goes back to Aditya rather than being built around; history:
  `documentation/decision-history.md`, 2026-08-17.
- **A match may only point backwards**, and a chain is followed: a requirement
  may name one that created no row of its own, and the evidence lands on the
  row at the end of that chain. Pointing forward is refused, never reordered.
- The row a within-batch match lands on keeps the **earlier** requirement's
  `What was asked` and recomputes `Written down?` across every requirement on
  it. The batch is read in workflow order (D04), so "earlier" means stated
  earlier in the work rather than named earlier in the alphabet.
- Every requirement index must return exactly once with a valid outcome, and
  with exactly one candidate named wherever the outcome names one. An
  incomplete answer fails the run; it never defaults to a guess.
- The three outcome words are a `Literal` on both answer models, so the
  generated schema refuses an invented outcome before the reply is read.
- **Match writes the question a person reads, and it is stored unchanged
  (2026-08-17).** Both answer models carry a `question`, and the prompts carry
  worked examples of the sentence. The rule follows the data, not the outcome
  word: a question is required wherever an answer names a register row — for
  either outcome, because a confident answer against a committed row is
  downgraded into the same possible-match decision — and wherever the outcome
  is `possible match`, which covers the within-batch pair that names no row.
  It is refused everywhere else. `MatchSettlement` carries it from the graph to
  `propose_rows`; nothing composes a sentence any more. A grouped
  observation-match decision stores its observations' sentences in answer
  order, joined by one blank line, character for character. History:
  `documentation/decision-history.md`, 2026-08-17.
- Each requirement reaches the Match prompt with its `document_type`, taken
  from the stored extraction and never guessed from a file name, so the
  question can name the kind of document each statement came from.
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
  moves: `Written down?`, which otherwise keeps denying a requirements document
  the row now cites. It holds one claim, so its old citation goes with its old
  value. On an
  already-committed row this writes the before-and-after audit entry and moves
  the fingerprint, exactly as an approved move does — a changed cell that left
  the fingerprint still would be the register lying about itself. History:
  `documentation/decision-history.md`, 2026-08-16.
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
  found issue, evidence, row, and human question; its answer is read from the
  decision it names (D02), not stored again.
- **A finding is five fields, and Examine writes the question itself
  (2026-08-17):** `rule_id`, `row_number`, `issue`, `evidence`, `question`. An
  empty question is refused beside an empty issue or evidence. The sentence is
  stored unchanged, states the rule in its own words, and carries no rule code
  — the person reading it has never seen the rules file. History:
  `documentation/decision-history.md`, 2026-08-17.
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
- **Who computes what:** every rule is judged by the model in one Examine call.
  An unusable rules file fails the run at the boundary and is never read as
  "no rules".
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
  verbatim:** `queued`, `running`, `needs review`, `done`,
  `export rejected`, `failed`, `no changes`.
- `done` means export exists. `export rejected` means export was rejected.
  `failed` is deliberate unrecoverable stop. Early exits use `no changes`
  plus a reason.
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

Seven slice-1 API endpoints:

| Endpoint | Job |
|---|---|
| `POST /projects` | Get-or-create the one project for a source folder (§ folder identity below); no name field |
| `GET /projects` | Every project, each with its runs nested, in one answer (L1) — the folders `POST /projects` may point at ride along too |
| `POST /runs` | Start/queue run by project id; return immediately |
| `GET /runs/{id}` | Durable status, stage, skips, failure, decisions |
| `POST /runs/{id}/decisions` | Answer one decision UUID |
| `POST /runs/{id}/finish-review` | Validate/claim review completion |
| `GET /runs/{id}/export` | Approved JSON or Markdown export |

`GET /runs` (every run, flat, newest first) is replaced by `GET /projects`,
not kept beside it — two list shapes for the same data was exactly the drift
this repository's conventions forbid. Superseded wording:
`documentation/decision-history.md`, "The screen becomes projects, and
inside each project its runs."

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
two must not be configurable into disagreeing. Startup seeds the demo project
with one `create_project` call for `sample-projects/intake-portal`;
get-or-create alone makes a restart safe. A `POST /projects` that created
nothing answers `200`, not `201`. **Implemented and verified** in slice-1
scope. **Limitation:** confinement is checked when a project is created, not
again when its folder is later read; nothing but `create_project` writes that
column, so no unconfined path can reach the database, but a folder replaced by
a symlink after creation is not re-checked.

### D15 — MCP and React

- MCP mirrors the seven endpoints 1:1: `create_project`, `list_projects`,
  `start_run`, `get_run_status`, `submit_decision`, `finish_review`,
  `get_export`.
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
  single run list — see `documentation/decision-history.md`):** projects
  (20rem), one selected project's runs (13rem, collapsible to a strip that
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
  Approve, Reject and Finish review. **A run panel has three tabs — Stages,
  Skipped, Decisions (locked 2026-08-16, superseding a fourth Register tab —
  see the register bullet below).**
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
- No blanket approve tool, waiting wrapper, separate MCP logic, state library,
  design system, dashboard, settings, or charts.
- **The screen polls `GET /projects` and `GET /runs/{id}` unconditionally, on
  the same fixed interval (`ui/config/screen.json`), whatever is on screen
  and whatever a run's status is (L1, locked 2026-08-15).** There is no
  per-project runs endpoint and no conditional refresh: at this size the
  payload is a few kilobytes, and one unconditional read is easier to reason
  about than conditional refresh rules. `GET /runs/{id}/export` is read only
  once a run's status says it exported. Nothing a person clicked is shown: an
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
  finished stages, and row count once exported), plus the projects root and
  the folders inside it, no cap on any list.
- **The register is the project's own panel, not a run's tab (locked
  2026-08-16, superseding the register-tab limitation below — history: "A
  folder is a project, and the register moves to the project").**
  `register_rows` was already keyed by `project_id` with `is_committed`, one
  register per project accumulating across runs; only the screen's
  presentation contradicted that. A `Register` entry sits above a project's
  runs in the middle column (`ui/src/RunColumn.jsx`), showing the row count
  of the newest run that has exported, if any; opening it shows the register
  in the right panel — the same panel a run opens into, reusing
  `ui/src/Register.jsx` unchanged — and clears whatever run was open, its
  export and both refusals, the same clearing rule `openRun` already
  follows. **No new endpoint and no new core function:** the panel is built
  from the two calls that already exist — `GET /projects` (runs newest
  first, each carrying `row_count`, non-null only once exported) to find the
  most recent exported run, then `GET /runs/{id}/export` for its register.
  Before any run has exported, the panel reads exactly "Nothing has been
  added to this register yet." — never an empty table.
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
  of adding a second one. `read_run_status` and `GET /projects`/`list_projects`
  both report it as an ordered list of stage names
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
  frozen per run, and the attachment audit event. Every rule lives in
  `config/rules.yaml`.
- The MCP slice is built: its six tools mounted in the same process over the
  same core functions the endpoints call.
- The incremental update slice is built: the watched folder, the read-once
  rule keyed by name or content, the rules-only route, and the byte-identical
  unchanged-row proof on both corpora. It added no tool.
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
   on 2026-08-14 with the run list and the Tailwind tokens, and resettled
   2026-08-15 into the three-column projects-and-runs shape (D15,
   `documentation/decision-history.md`) — item 5 below is resolved by it.
3. Whether real document sizes justify pgvector retrieval or Extract fan-out.
4. Exact later-slice storage choices where this file explicitly leaves them
   open; do not invent them before their slice.

## Known limitations and unverified assumptions

- No live model call has run; provider quality, exception shapes, latency, and
  cost are unverified.
- Register-size and short-document assumptions remain unmeasured on full demo
  and second-run corpora.
- The page limit binds `.pdf` only; no other declared format reports pages.
- A handover summary that lists requirements, in a run that never exports, is
  read again by the next run.
- Rules about elapsed time cannot be judged: the register keeps no document
  dates.
- Work stopped by something outside the provider's control is reported through
  the source document, not through a cell of its own.
- A batch holding two documents of one type orders them by file name.
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
| Five/six API endpoints; flat `GET /runs` run list | D14 seven endpoints including `GET /projects`, every project with its runs nested |
| `done` as generic terminal state | D13 honest `failed`/`no changes`/`export rejected` |
| Status-only already-read check | D03 extraction + export/unrelated/no-requirement rule |
| Already-read matched by name AND content; requirement withdrawal | D03 read-once rule matched by name OR content; withdrawal removed |
| Unmarked emptied merge proposal | D09 `merged_into_register_row_id` |
| Missing Match outcomes default to new rows | D09 complete exact coverage or failure |
| Non-atomic finish-review read/launch | D02 atomic claim plus future replay marker |
| Non-idempotent Ingest/Match re-entry | D12 unique/upsert Ingest + replace-own-uncommitted Match |
| `audit.cell_name NOT NULL` for every event | D06 `event_kind` with a nullable cell name for attachments |
| Code-composed review questions in `propose_rows`, `move_rows`, `found_issue` | D09/D10 the model writes the sentence and it is stored unchanged |
| The export carrying `reported_instructions` | D05 the run payload and the Reported tab carry it; the export does not |

For full chronology, alternatives, trade-offs, evidence language, and all 93
original Decision Log rows, use `documentation/decision-history.md`.
