# PROGRESS.md — current project dashboard

Current status only. Completed narrative that has fallen out of this file
stays in its own Git history — `git log -p PROGRESS.md` reaches all of it.
Decision rationale belongs in `DECISIONS.md`, not here.

## Snapshot — 2026-08-25, branch `codex/task1-eight-findings`

The watcher repair removes mixed-trigger duplicates. If a manual or queued
run settles every file in the watcher's changed signature, the watcher marks
that signature served instead of adding a second `no changes` run. It still
starts the next run for a file that missed the active batch, and an unsupported
arrival still gets one run with one `not read` reason. Both new duplicate tests
were observed failing first; the complete watcher file is now **5 passed**, and
the wider watcher/queue/run-ending set had **12 existing tests pass** before a
new fixture-only assertion was corrected and re-run green.

The documentation/UI drift pass points README at the current `Run` tab, documents the
shipped 2-second poll and 5-second quiet window in `config/README.md`, and
bundles an SVG favicon under `/ui/`.

The in-app Browser drove the four Helpline files sequentially and a second
Helpline project in batches, including the three-column screen, both rails,
review buttons, History, a 900px viewport and a clean console. MCP discovery
returned exactly eight tools; queue/dedupe behaviour and MCP/HTTP parity were
checked. A no-bind image first reproduced the hidden 503 UI packaging gap; the
final multi-stage image migrated fresh PostgreSQL and served health, `/ui/`,
and `/ui/favicon.svg` with HTTP 200. The corrected release proof is **298
Python passed** against real PostgreSQL and **116 front-end passed across 50
files**; the production UI build also passes.

## Snapshot — 2026-08-24, branch `brief-2-screen`

The screen half of the demo-run repairs: after this branch the review screen
shows what the backend already built, and composes no sentence of its own.

- **A run is three tabs** — `Run`, `Skipped`, `Reported instructions`, each
  wearing a count only above zero. The Run tab reads top to bottom: the stage
  strip (the Review box says "waiting for you", later stages of an ended run
  say "not started"), the ended-early sentence, the waiting block with both
  endings — Add disabled while a decision is unanswered and the count on the
  line — then the decisions, then the rules. The section numbers, the Decisions
  tab and the two hardcoded sentences are gone.
- **A decision card renders the backend's own blocks.** `question` is split on
  the blank lines it was built with, and which block is which is read off the
  parts (`rule_text`, `issue`, `quotes`) rather than off what a block says, so
  no sentence is parsed or rebuilt. `Question.jsx` writes none of its own; the
  chosen answer keeps the accent, and both stay live until the review ends.
- **The Skipped tab is three groups by kind**, one line per entry, and an
  observation that reached no row is titled by what it says. A place is named
  only where the server sent one.
- **The register page is two tabs, and a row opens a panel.** `Register · n`
  and `History · n runs`; the first column is `Row`; a row with findings wears
  a `1 finding` mark beside its status and a clean row wears none. The panel
  carries the four cells, the evidence in payload order with the cells each
  quote supports, the findings keyed on `finding_id` with the run that raised
  them, and that row's own history, collapsed. History is grouped under the run
  that changed the register, and the run heading names no file.
- **Both side columns collapse to a rail** that still opens the register and
  every run; a run's mark is its plain number. Every clickable thing carries a
  pointer, a hover state and a pressed state.
- **The address names what is on screen**: `?project=<id>&run=<id>`, written by
  one effect, read back on load in all three shapes.
- **`citations` and `examine` left the register JSON** (`export_register.py`),
  with `examine_as_exported` removed as the orphan it became. The Markdown
  export already read only the new fields.

**Both suites green, no live key: 292 Python passed** and
**114 front-end passed across 48 files**. One assertion was added to
`tests/register/test_the_register_is_read_live.py` after that full run and
proven by running that file on its own. The four demo documents have not been
re-driven on a clean database since Brief 1a; that is still the foreground step
after this branch merges.

**Assumptions made on this branch, so they are findable later.**
- With the register panel open the address carries `?project=<id>` alone. Item
  9 names the two shapes a run and a project take and says nothing about the
  register, and a third shape would need a word for the register in the query
  that nothing else uses.
- The Add-project button reads "Create project" only for a folder the server
  has actually reported as holding no file. Before a folder is chosen, and for
  a folder `has_files_by_folder` says nothing about, it reads "Create and start
  run" — the ordinary ending, rather than a guess about an unknown folder.
- The consequence sentences beside Approve and Reject are the last block of
  `question` with the backend's own `Approve → ` / `Reject → ` marker taken
  off, rather than being rebuilt from `if_approved`. The marker is a constant
  of `app/review/decision_text.py`; rebuilding would have meant writing the two
  sentences a finding and an evidence-only merge carry, which `if_approved`
  does not hold.
- Item 32 is proven structurally rather than by measurement: jsdom does no
  layout, so the test asserts that both labels and both consequence sentences
  are children of one grid, which is what makes them align at any width.
- The `#`-before-a-digit sweep over the screen walks `ui/src` and skips
  `screen.css`, the one file that is nothing but colours; hex colours are taken
  out of every other file before the search.

## Snapshot — 2026-08-24, branch `brief-1b-sentences-payload-export`

The reading half of the demo-run repairs: after this branch every sentence a
person meets on a decision, an evidence line, the Skipped tab or the Markdown
export is written by the backend from stored data, in one vocabulary.

- **The backend builds every decision sentence** (`app/review/decision_text.py`).
  `question` has left both Match answer models and the Examine `FoundIssue`
  model with the refusals that guarded it; the whole text a person reads is
  frozen in `decisions.question` and the same text taken apart in
  `decisions.parts` (migration `20260823_0025`). The one exception is a
  finding's issue line, which stays the model's because only the rule can say
  what breaking it looks like.
- **One source line everywhere** (`app/ingest/source_line.py`): `<file>, under
  "<Heading>"` / `<file>, before the first heading` / `<file>, page <n>`, with
  `, says:` appended by a decision. A quote found twice names its first place
  only; `locate_quote` no longer stores a comma-joined list.
- **`not_used` is `skipped`** (migration `20260823_0024`), on the column, the
  payload and the MCP tool, with kinds `read before` / `not read` / `not
  attached`. An entry that reached no row carries its own source line, or
  `null` where the words were never in the file.
- **The register read carries `evidence`**: citations merged by quote, each
  naming the cells it supports, ordered by when the evidence arrived. The
  Markdown export is rendered from that field alone — `Row` heading, per-row
  Evidence, Findings only when there are some, and a closing Rules section —
  with no rule id and no `#` before a number anywhere.
- **An empty folder makes a project and starts no run**, refused identically
  through `POST /runs`, the MCP tool and the watcher; the folder list says
  which folders hold a file.
- **The watcher polls every 2s and waits 5s of quiet.**

**Both suites green, no live key: 289 Python passed** and **66 front-end
passed across 38 files**. The four demo documents have not been re-driven on a
clean database since; that is the foreground step after this branch merges.

**Assumptions made on this branch, so they are findable later.**
- The locked sketches of the three decision shapes are aligned for a
  monospace reader. The stored text normalises that: blocks separated by a
  blank line, single spaces after `→` and after each colon, two spaces
  between two cells that change on one line. `tests/register/test_review_
  question_wording.py` is the canonical form.
- `if_approved` is always a list of `{cell, value}` and is empty where
  approving writes no cell; `if_rejected` is always one sentence. A
  possible-match approval that writes nothing says the row stays as it is and
  the ask's evidence joins it.
- A possible-match reject line names the proposed row's own `Written down`
  value, which is `Not known yet` when only a meeting note states the ask.
- The `Register row N` / `Row N (proposed by this run)` split is the
  possible-match decision's alone (S24). An observation match and a finding
  say `Register row N`, as their locks show.
- An absence entry in `evidence` carries `source_line: null`: a silence has no
  place to point at, and the sentence names the file.
- The folder list carries `has_files_by_folder` beside `available_folders`
  rather than a flag inside each entry.
- The Markdown Rules section still prints a rule's `params` beside its text;
  a rule naming a limit cannot be read without its value. No shipped rule has
  params today.
- Item 39's plain-text prompt rendering was **not** done: three test markers
  (`MATCH_BATCH_MARKER`, `EXAMINE_ROW_MARKER`, `EMPTY_REGISTER_MARKER`) are
  built on the JSON rendering, so it is not the few-line change the brief
  allowed for. It is moot as a bug — no model-written sentence reaches a
  screen any more.
- `RunEngine` gained `project_root`, because the empty-folder check resolves
  a project's folder relative to the repository and all three doors reach the
  one function.

## Snapshot — 2026-08-23, branch `brief-1a-pipeline-and-schema`

The pipeline half of the demo-run repairs: after this branch the register's
cells, findings and history say what the documents actually support.

- **The status `Nothing said yet` is `Requested`** (migration
  `20260823_0022`), everywhere a reader or the system takes the word from.
  A grep for the old words over the repository hits only the places that
  record them on purpose: the two rename migrations and their two tests
  (`test_schema.py`, `test_requested_status_migration.py`), the DECISIONS
  replacement notes, this line and the live-run row below, and the live-run
  record under `documentation/` — never `app/`, `ui/`, `config/` or README.
- **Cells are short, and the file behind an answer is in the evidence.**
  `Written down` reads `Not known yet` · `Yes` · `Not mentioned`;
  `What testing found` reads `Not known yet` · what testing said ·
  `Not mentioned`.
- **The absence move is built** (`app/register/absence_rows.py`), the feature
  this file listed as not built. Match works out which rows each client
  requirements document and testing report the project has read does not
  mention and stores that beside the observations' moves; Examine judges the
  register with those absences overlaid, and Commit writes them: the cell
  moves to `Not mentioned` with the file as its evidence, its history entry
  and a moved fingerprint. It never overwrites an answer, and a run that read
  such a document always continues to Review.
- **A rule waits for the documents it is about** (`applies_when` in
  `config/rules.yaml`, validated at startup and at every freeze), and
  `runs.rules_applied` (migration `20260823_0023`) records exactly what
  Examine sent to the model.
- **The register shows each rule's finding from the latest run that applied
  it**, so a row never carries two copies of one rule's finding again.
- **Examine treats an unanswered possible match as the match**: it judges the
  row the proposal would join, with that proposal's `Written down` overlaid,
  and counts real rows only.
- **One definition of "read"** (`app/ingest/read_once.py`), shared by Ingest,
  the rule gate and the absence move.

**Both suites green, no live key: 272 Python passed** and **66 front-end
passed across 38 files** (merged as PR #40). The corpus has not been driven
against a live model since; the expected end state is in
`sample-documents/helpline-ai/README.md`.

**Assumptions made on this branch, so they are findable later.**
- The tests that drive a batch of meeting notes and still expect a rule to be
  checked use a rules file with no `applies_when`
  (`tests/examine/rules_files.py`) — item 24 allows a missing field to mean
  "always applies".
- The register JSON's `findings` entries gained `raised_by_run` and
  `finding_id`.
- A `done` run from before this branch has `rules_applied` null, so its
  findings no longer show on the register (History keeps them). A fresh
  database never has such a run.
- The register JSON's `examine` block and per-row `citations` list left the
  JSON on the screen branch, once nothing read them.

## Snapshot — 2026-08-19, branch `live-run-repairs`

Two more defects the live run exposed, both fixed test-first.

- **A conflict was being dropped because the two documents arrived in
  different runs.** `_cells_the_observations_move` read `delivery_claimed`
  from this batch's observations alone, so a handover in run 4 and a testing
  report of absence in run 5 settled the row on `Not delivered` — while the
  row's own citations still carried the handover claiming delivery. The same
  two documents in one batch gave `Disputed`. The row's standing
  `Handed over` status now counts as the claim it is.
  `test_a_handover_from_an_earlier_run_still_opposes_a_later_absence_report`
  failed at the baseline on `assert 'Not delivered' == 'Disputed'`.
- **Control characters the model writes no longer reach a cell.** A live
  reply came back with U+0014 where an em dash had been sent, and it reached
  the register's findings section and the screen. `call_the_model` strips C0
  control characters — written either as themselves or as the JSON escape —
  from every reply, keeping newline, tab and carriage return.
  `test_a_control_character_the_model_wrote_never_reaches_a_cell` failed at
  the baseline on the character surviving into the requirement's summary.

**Both suites green, no live key: 253 Python passed** and **63 front-end
passed across 36 files.**

## Snapshot — 2026-08-18, branch `strict-schema-and-honest-early-exit`

The first live-key run started and stopped on its first model call. Three
defects, each found by running rather than by reading, each fixed test-first:

- **The key never reached the container.** `docker-compose.yml` read
  `OPENROUTER_API_KEY` from `.env` for its own substitution but passed it into
  no service, so a fresh clone following `README.md` had the key on the host
  and none inside the app. Observed directly:
  `'OPENROUTER_API_KEY' in os.environ` printed `False` in the container, and
  `True` after the fix. Fixed on `main` as `6908375`, with
  `tests/infrastructure/test_the_model_key_reaches_the_app.py` failing at the
  baseline on exactly that missing forward.
- **The provider refused our strict schema outright.** OpenAI strict mode
  rejects a `$ref` carrying any sibling keyword, and Pydantic writes a field's
  `description` beside the `$ref` it generates for an enum. The live 400 read
  `Invalid schema for response_format 'ExtractionAnswer': context=('properties',
  'label'), $ref cannot have keywords {'description'}`. Exactly two places
  generated one — `ExtractionAnswer.document_type` and
  `QuotedTestingObservation.label`. `_tightened` now returns a lone `$ref`.
  The field descriptions on those two enums are lost to the provider; the
  prompt's own type table and the enum values still carry the meaning.
- **A run reported reading documents it never read.** With every document
  failing at Extract, `_early_reason` still answered "The documents were read,
  but none of them stated a requirement", because it branched on the documents
  Ingest collected rather than on the documents Extract actually read. The
  state now carries `documents_read`, and a run that read nothing says
  "Nothing was read — all N files were not used. See the Not used tab for
  why." This is the no-bluff rule, caught live.

**The failure contract itself behaved correctly** and needed no change: the
400 degraded one document instead of killing the run, the file was recorded
`not read` with its reason, and the run ended `no changes` saying the next run
reads it again.

**Both suites green on this branch, no live key: 249 Python passed** (246 on
`main` plus the key test and the two new never-do tests) and **63 front-end
passed across 36 files**.

## Snapshot — 2026-08-18, branch `helpline-ai-corpus`

Built and run rather than type-checked, committed and pushed.

- **Reviewed (Fable 5, review-only — Codex is retired, its limits exhausted)
  and the one Medium finding fixed in the foreground after Aditya decided it
  (2026-08-18):** `DECISIONS.md` still cited the deleted
  `test_second_run_on_corpora.py` and "both synthetic corpora",
  present-tense, as the standing unchanged-row proof; the three stale
  citations now name `tests/incremental/test_incremental_updates.py` as the
  surviving proof and date the corpus removal. Documentation-only fix — no
  code or test changed, so the foreground suite runs stand.
- **Both suites re-run independently in the foreground after the review:**
  **246 Python passed** and **63 front-end passed across 36 files**, read
  from the suites' own printed summaries.

- **The old sample corpora and the startup demo seed are gone.**
  `sample-projects/intake-portal/`, `sample-projects/northside-dental/`, and
  `sample-projects/write_northside_dental_binaries.py` are deleted.
  `ensure_demo_project`, `DEMO_PROJECT_FOLDER` and the `app/main.py` call that
  used them are deleted from `app/projects/create_project.py` and
  `app/main.py`; the `async with pool.connection()` block in `app/main.py`
  that held only that call is removed too. `docker compose up` now starts
  with **zero projects** — a project exists only once an operator creates one
  by hand, through the screen's Add-project box or the MCP `create_project`
  tool.
- **Test-first, per the brief's protocol.** The never-do test
  `tests/projects/test_startup_seeds_no_project.py`
  (`test_startup_creates_no_project_of_its_own`) was written and run at `main`
  `f6ca05d`, before any deletion: it **failed**, `GET /projects` listing the
  demo project ("Intake Portal") that startup had just created. It passes
  once `ensure_demo_project` and its call are gone.
- **Old-corpus tests are deleted, not adapted.**
  `tests/incremental/test_second_run_on_corpora.py` (2 tests) and
  `tests/documents/test_document_instruction_is_reported.py` (1 test) read
  the real corpora from disk and are deleted whole; no replacement
  corpus-driving tests are written. Reported-instruction coverage stays live
  in `tests/runs/test_reported_instructions.py`, which builds its own
  document in a temporary folder — confirmed still green.
  `tests/projects/test_create_project.py` and
  `tests/interfaces/test_mcp_tools.py` were grepped for a test that exercises
  `ensure_demo_project` or the demo seed specifically; neither file has one,
  so neither file's test functions were touched (both carry stale comments
  mentioning the demo seed that are out of this brief's scope).
- **A new corpus for the coming live-key run: Helpline AI.** Four documents
  under `sample-documents/helpline-ai/` — a fabricated engagement, client
  BrightCart, an AI customer-support product for it — carrying the brief's
  seven requirements at the client's own granularity, and the three rule
  hooks the brief's design calls for (written-requirement, change-request,
  testing-outcome); the fourth rule is expected to find nothing, by design.
  The corpus's own README states the expected end-state table, labelled as
  the live run's expected outcome, not an acceptance check for this branch.
  `sample-projects/helpline-ai/` is git-ignored so staged copies never dirty
  the tree; the corpus is staged into it by hand, in batches, and **never**
  driven through the pipeline here — no scripted model fixtures exist for it.
- **Documentation grepped and fixed**: root `README.md` (startup behaviour,
  the included-demo-folder paragraph), `sample-projects/README.md` (rewritten
  — starts empty, points at the staged corpus), `DECISIONS.md` (D14's
  startup-seed wording, D08's and the acceptance summary's demo-document
  citation, a known-limitation line naming the deleted corpora), and
  one dated `DECISIONS.md` entry (the old wording, why superseded, the corpus
  replacement).
- **Both suites green on this branch, no live key:** **246 Python passed**
  and **63 front-end passed across 36 files** (untouched by this branch — no
  `ui/` file was edited). Both counts are read from the printed summary.
  **Inference, not verified:** `main` at `f6ca05d` most likely collected 248
  (the `247` recorded in the prior snapshot was measured before that branch's
  post-review fix added one more test); 248 − 3 (the two deleted files' tests)
  + 1 (the new never-do test) = 246, matching what was printed here. The
  baseline itself was not re-collected on this branch to confirm 248 directly.
- **Boot check, hand-driven** (compose, no key): `GET /projects` answered
  `{"projects": []}` on a fresh database; `mkdir`-ing a folder directly inside
  `sample-projects/` and calling `POST /projects` over it answered
  `{"created": true}`, and the project then appeared in `GET /projects`.
  Torn down after.
- **Observed, out of scope for this branch:** running the Python suite via
  `docker compose run` leaves a restricted-permission leftover directory
  under `sample-projects/` when `test_a_folder_outside_the_projects_root_is_refused`'s
  `shutil.rmtree(..., ignore_errors=True)` cannot remove what it created —
  pre-existing behaviour, unrelated to the corpus replacement; cleaned by
  hand after each run in this session.

Everything below is the position this branch started from; the prior
branch's own snapshot (`audit-history-read`) is in this file's Git history.

## Completed

### The audit trail becomes readable (branch `audit-history-read`)

- **Test-first, recorded at the baseline commit `bdb360e`.** Python:
  `8 failed, 239 passed`. The eight were the two count-lock tests updated to
  say eight (offered seven, locked list said eight), five of the six new
  history tests, and the new both-doors test (`get_history` not listed). The
  sixth, `test_the_register_document_carries_no_history`, passed at baseline
  by design — it guards the decision that the register document is untouched,
  so it is a lock rather than a detector, and it still passes. Front end:
  `3 failed, 60 passed across 36 files`, all three failing because the HISTORY
  region did not exist.
- **After the change:** Python `247 passed`, front end `63 passed across 36
  files`.
- Built: `app/register/read_history.py` (the one core function),
  `GET /projects/{project_id}/history` in `app/api/routes.py`, the
  `get_history` tool in `app/mcp_server/tools.py`, `readHistory` in
  `ui/src/run_requests.js`, `ui/src/History.jsx`, and the section and its
  own read/refusal state in `ui/src/ReviewScreen.jsx`. `CELL_HEADINGS` is now
  exported from `ui/src/Register.jsx` and imported rather than copied.
- Ordering is fixed in the query — newest `created_at`, then `row_number`,
  then `cell_name` nulls last — because one run's entries all carry that
  transaction's single timestamp. Run numbers use the same window function
  `app/projects/list_projects.py` uses.
- **Assumption recorded:** the brief said `LOCKED_TOOLS` should gain
  `get_history` "in the server's registration order (after `get_register`)",
  but `tests/interfaces/mcp_client.py` returns `sorted(...)` and the test
  asserts list equality, so the entry sits in alphabetical position (before
  `get_register`) while the tool itself is registered after `get_register` in
  `app/mcp_server/tools.py`, as the brief separately requires.
- **Assumption recorded:** the history read has its own refusal state rather
  than sharing `readRefusal`. The run read and the register read may share one
  because they are mutually exclusive; the history and register reads run on
  the same poll, concurrently, so a shared value would let either wipe the
  other's live refusal.
- **Not built, deliberately:** revert/restore, register version snapshots,
  filters, search, pagination, and a history export format.

### The register is read live, and the snapshot goes (branch `register-read-live`)

From `main` at `f6aa015`, the trap first, then the live read, the migration,
the screen, and documentation. Item C2 of the review checklist; superseded
entry: "The register is read live, and the snapshot goes (2026-08-18)".

- [x] **The never-do tests were written and run at the baseline before any
      code changed.** Six failed there for the right reason: the four in
      `tests/register/test_the_register_is_read_live.py` because
      `GET /projects/{id}/register` did not exist, and the two in
      `tests/interfaces/test_register_reads_identically_from_both_doors.py`
      on `Tool 'get_register' not listed` and on the route set still holding
      `('GET', '/runs/{run_id}/export')`. The two in
      `tests/incremental/test_read_once_follows_the_run_status.py` passed at
      the baseline by design — they guard the swap rather than detect it —
      and passed again after it.
- [x] **The `collect_batch` swap, first and on its own commit:**
      `runs.export_json IS NOT NULL` became `runs.status = 'done'`, after
      re-verifying on `f6aa015` that the commit node writes the rows and the
      status inside one `connection.transaction()`. Observed after the swap:
      both corpora's second runs counted every document `not_used` with kind
      `already read` and made no new Extract call; a document read only by a
      `discarded` run was read again (two Extract calls recorded); the
      transient-failure, edited, renamed, deleted, unrelated and
      asked-for-nothing paths all behaved unchanged — 15 targeted tests
      passed.
- [x] **One core function serves the register live:**
      `build_register_document` reads `register_rows WHERE is_committed`
      with citations, approved findings, and the newest `done` run's examine
      section and `finished_at` as `exported_at`; `read_register` serves
      JSON and Markdown from it; the route and the MCP tool are thin
      wrappers over it, byte-identical by test. A project with no committed
      rows answers `200` with an empty register; the Markdown reads the
      screen's own empty line.
- [x] Migration `20260818_0021` drops `runs.export_json`; the downgrade
      re-adds it nullable and empty and says the snapshots are not
      reconstructible. `run_status`'s `exported` key derives from
      `status == 'done'`; `list_projects` reports a `done` run's `row_count`
      as the project's committed rows, counted live.
- [x] The screen's Register panel makes one GET of the register route; the
      walk over the project's runs, the `run.exported` read and the
      `projectsRef` machinery died with it. The empty state keys on the
      register holding no rows.
- [x] Snapshot-contract expectations updated to the live contract — the
      409-before-commit reads now expect `200` with an empty register, the
      `exported` derivation follows the status, and every register read in
      the suites goes through the project-level route. No already-read test
      was weakened.
- [x] Hand-driven against the live stack; see `## Verification evidence`.

### `skipped` becomes `not_used`, and every entry says its kind (branch `skipped-becomes-not-used`)

From `main` at `bb48974`, server first, screen second, tests last.

- [x] **The never-do tests were written and run at the baseline before any
      code changed**, and each failed there for the right reason:
      `test_a_not_used_entry_names_whether_the_file_was_already_read_not_read_
      or_dropped` with `KeyError: 'not_used'`;
      `test_both_doors_call_the_list_not_used_and_report_the_same_entries` on
      `assert "skipped" not in over_http`;
      `test_the_rename_carries_every_entry_across_and_the_downgrade_carries_it_
      back` with `UndefinedColumn: column "not_used" does not exist`; and both
      front-end tests in `every_not_used_entry_wears_the_label_its_kind_names`
      because no tab was named `Not used`.
- [x] Migration `20260818_0020` renames `runs.skipped` to `runs.not_used` and
      nothing else. Proven by hand on a real database: seeded at
      `20260817_0019` with two entries, `md5(skipped::text)` recorded, upgraded
      (column gone, `not_used` present, `NOT NULL` and `'[]'::jsonb` default
      carried, same md5), downgraded (`skipped` back, same md5), upgraded again
      (same md5). No constraint and no index names the column — read off the
      real database with `pg_get_constraintdef` over `pg_constraint` and
      `pg_indexes` for `runs`, not taken from the migration files.
- [x] Four kind values became three, named once in
      `app/runs/not_used_kinds.py`. `SKIPPED_FILE_KIND` split into
      `ALREADY_READ_KIND` and `NOT_READ_KIND` at its four call sites;
      `SKIPPED_DOCUMENT_KIND`'s four call sites in `register_graph.py` are all
      `NOT_READ_KIND`; `SKIPPED_OBSERVATION_KIND` and every dropped quote
      became `DROPPED_KIND`. No old constant survives.
- [x] In `read_document.py` the entry's `kind` key and its reason sentence no
      longer share one variable: the key takes `DROPPED_KIND` and the
      sentence's `quote_kind` still names the quote's own kind.
- [x] `append_skipped` became `append_not_used`, reading and writing
      `runs.not_used`; its whole-entry reconciliation is unchanged, so a
      replayed stage still records nothing twice.
- [x] `ReviewScreen.jsx`'s second tab reads `Not used`, its count line reads
      `N not used`, its empty state reads `Nothing in this run went unused.`,
      and each card wears the label its `kind` names — from `NOT_USED_LABELS`
      alone, with no default and no label for an unrecognised kind. The run's
      `ended_early_reason` follows the tab's word too.
- [x] Hand-driven, scripted model and no live key: a first run recorded one
      `dropped` entry (reason still "…so this requirement was dropped.") and
      one `not read` entry; the second run over the untouched folder recorded
      two `already read` entries and ended with "Nothing was read — all 2 files
      were not used. See the Not used tab for why." The payload carried
      `not_used` and no `skipped` key.

### The gate becomes one button, and a refused run is discarded (branch `gate-becomes-one-button`)

From `main` at `963c3a7`, in two parts, the rename first and alone.

**Part 1 — `export rejected` becomes `discarded`.** `CLOSED_WITHOUT_EXPORT`
keeps its name and changes its value; migration `20260817_0019` follows the
rename pattern of `20260816_0014` — drop `ck_runs_status`, rewrite stored rows,
recreate the constraint. Neither partial unique index on `runs` names the value,
read off a real database with `pg_get_constraintdef` and `pg_indexes` rather
than taken from the migration files, so no index was rebuilt. No machinery was
renamed: `export_json`, `GET /runs/{id}/export` and `build_export` are
untouched. The register header now reads `last updated` instead of `exported`;
`exported_at` is unchanged.

**Part 2 — one press ends the review.** The Review node no longer raises the
export decision. `finish_review(engine, run_id, add_to_register)` writes it —
question and answer together, the same question sentence as before — inside the
same `claim_review_finished` transaction, so the caller that loses the race
writes nothing. `POST /runs/{id}/finish-review` and the MCP `finish_review` tool
both carry the argument into that one core function; the endpoint refuses a call
that omits it with the body to send (400), and the three existing refusals —
unanswered decisions, not at review, finished a moment ago — are word for word
what they were. The screen offers `Add this run's changes to the register` and
`Discard this run's changes` under the same rule the old button followed, and
filters the export decision out of the queue in one place so the count and the
cards cannot disagree.

**Test-first, and the baseline failures were recorded before any source
changed.** On `963c3a7` the eight new Python cases failed —
`tests/infrastructure/test_discarded_status_migration.py` (2),
`tests/register/test_one_press_ends_the_review.py` (4) and
`tests/interfaces/test_both_doors_end_the_review_alike.py` (2) — **8 failed**,
every one a real assertion: `DID NOT RAISE`, `'done' != 'discarded'`,
`['export', 'finding'] == ['finding']`, `409 == 400`, and four timeouts waiting
for `done`/`discarded`. The new front-end file printed **4 failed, 2 passed**:
the gate still rendered as a question, and neither ending button existed. The
two that passed there are regression guards — the offering rule already refused
to show an ending while a decision was unanswered, and the screen already
printed the stored status verbatim.

**Existing tests updated to the one-press contract — the deliberate change,
listed so it can be checked.** The shared helper and every direct
`finish-review` call gained `{"add_to_register": true}`; the approved-export
test now presses once and reads the recorded decision back; the two
replay-guard tests read the export decision after finishing rather than before,
because it does not exist before; the pending-decision refusal, the MCP flow
and two MCP tool tests were given a real finding to leave unanswered, since the
gate is no longer a queue question; the rejected-export incremental test now
presses discard; the two wording tests read the frozen question off the
decision the press wrote. No test of the review contract — the refusals, the
atomic claim, the replay guard — was weakened.

**One change outside the file list, and why.** `app/register/read_export.py`'s
refusal told a caller to approve the export decision and then finish the
review, a flow that no longer exists; it now names the one call and the body
that produces an export.

### The model writes the review question, and three prompts are rewritten (branch `wording-and-prompts`)

From `main` at `1a03ceb`. Match's two answer models and Examine's `FoundIssue`
each gained a `question`, and the three code-composed sentences in
`propose_rows.py`, `move_rows.py` and `found_issue.py` are gone. The rule
follows the data: a question is required wherever a Match answer names a
register row — for either outcome, because a confident answer against a
committed row is downgraded into a possible match upstream — and wherever the
outcome is `possible match`; it is refused everywhere else. `MatchSettlement`
carries the sentence from the graph to `propose_rows`. A grouped
observation-match decision stores its observations' sentences in answer order,
joined by one blank line, character for character. What Approve and Reject do
is code-owned fixed text, delivered as `row_number` and `moved_cells` on the
decision payload and rendered by `ui/src/Question.jsx`. The export no longer
carries reported instructions; `GET /runs/{id}` still does, and no migration
was needed. The Reported tab says its notice once above the cards, in the
plural, and its empty state names what was looked for.

**Test-first, and the baseline failures were recorded before any source
changed.** On `1a03ceb` the eight new Match refusal cases in
`tests/match/test_the_question_a_match_carries.py` and the two new Examine
cases in `tests/examine/test_examine_answer.py` failed — **10 failed, 5
passed** — and the six front-end cases across the two changed UI test files
failed — **6 failed, 1 passed**. Every failure was a real assertion, not an
import error.

**Assumptions made here, so they are findable later.** The consequence block's
field names (`row_number` widened from a finding's own row to the row any
decision is about, and `moved_cells`) are this brief's choice, not a lock from
an earlier one; `COLUMN_HEADINGS` moved from `app/register/export_register.py`
to `app/register/cells.py` because the review payload now prints cell names
too. The two test-helper questions in `tests/documents/register_documents.py`
stand in for sentences the model writes at run time; no live-key run has yet
shown what a real model writes into these fields.

**Codex's one finding repaired in the foreground, on the same branch, after
Aditya decided it.** The misplaced-question refusals tested the stripped value,
so a blank non-null `question` slipped past where any non-null one must be
refused. Both guards now test `question is not None`; the two tests were
written first and seen failing on `DID NOT RAISE`
(`test_a_new_row_carrying_a_blank_question_is_refused` and its observation
twin). After the repair the Python suite printed **216 passed** and the
front-end suite was not re-run — no front-end file changed in the repair.

### The register becomes four cells (branch `register-becomes-four-cells`)

Eight parts, one commit each, from `main` at `85e97bb`. Baseline counts printed
in this worktree before anything changed: **195 Python tests and 44 front-end
tests across 29 files**.

- **Part 6** — `app/examine/deliverable_checks.py` deleted. D1 was already dead
  code (a row is written with its `what_was_asked` citation in the same
  function that creates it), and `commit_register` already refuses to commit a
  row carrying no citation; that refusal's message no longer cites a deleted
  rule. D2 became `R5` in `config/rules.yaml`.
- **Part 7** — `.docx` and `.txt` removed with `app/ingest/read_docx.py`, the
  `python-docx` pin, `line_number_at`, four test files' worth of coverage and
  the Northside `.docx`, which is now `client-requirements-v1.md`. The skip
  reason names the two formats that remain.
- **Part 8** — `related additional document` renamed `handover summary` in the
  enum, the prompt's type table, the tests and the documentation.
- **Part 1** — `CELL_NAMES` narrowed to four; migration `20260817_0017` drops
  `blocked_on`, `first_seen` and `last_moved`, deletes the citations naming
  them, and swaps `Blocked` for `Handed over` in `ck_register_rows_status`. The
  export and the screen head the cell `Written down` while the stored column
  stays `in_writing`.
- **Part 3** — `status_after` returns `Handed over` for delivery evidence with
  no testing behind it.
- **Part 4** — `_requirements_of_batch` sorts by `workflow_position` before
  file name.
- **Part 5** — a `Status` move drops only the citations of the verdict it
  supersedes and keeps the rest, so the handover's citation survives the move
  to `Done`.
- **Part 2 was not built.** See `## Active blockers`.

**Migration evidence, driven by hand against a real database.** Seeded at
`20260816_0016` with one committed row per status including `Blocked`, each
citing all seven of its cells. `alembic upgrade head` refused with
`1 register row(s) are 'Blocked' — #6 — … change its status, then run this
migration again`, and the whole step rolled back: `pg_get_constraintdef` still
named `Blocked`, `information_schema` still held the three columns, and all
seven cell names still appeared in `citations`. After changing that one row's
status the upgrade completed — the constraint read `Done, Partial, Not
delivered, Handed over, Disputed, No evidence yet`, the three columns were
gone, and only the four cell names were left in `citations`. `alembic downgrade
20260816_0016` put the three columns and `Blocked` back without refusing
anything (it widens: `Handed over` stays, because a row written since may hold
it), and upgrading again reached the same four-cell shape. No fingerprint was
recomputed by the migration; the next run that touches a row writes the right
one.

**Both corpora driven end to end, in two arrival orders.** Intake portal as
`[M1] [M2] [C] [T]` and as `[M1 M2] [C T]`; Northside Dental as
`[M1] [M2] [C] [H] [T+leave policy]` and as `[M1 M2] [C H] [T+leave policy]`.
Each corpus ended with the same register in both orders, cell for cell and
citation for citation. Northside row 1 ends `Done` citing both
`handover-summary.md` and `testing-feedback-15-jul.pdf` on `Status`, which is
Part 5 shown on real documents. The Northside corpus still runs with its
requirements document as `.md`.


### Product and architecture

- [x] Domain, actors, workflow boundary, deliverable, user, run scope.
- [x] Human-gate scope/actions and review queue.
- [x] Register cells/statuses, citations, export, audit/fingerprint contracts.
- [x] Pipeline, model boundary, state/checkpoints, failure/retry contract.
- [x] Run identity/statuses/lock/queue design.
- [x] Watched-folder, rules/findings, MCP, React, cost/timing designs.
- [x] Brief-behaviour acceptance contract and vertical-slice order.

### Slice 1 implementation and proof

- [x] PostgreSQL migrations and seven domain tables.
- [x] `.md` batch collection, exact quote location, extraction, matching.
- [x] Possible-match review, atomic finish-review claim, commit, export.
- [x] Six API endpoints and startup project seeding.
- [x] `failed`, `no changes`, `discarded` semantics.
- [x] Configuration-vs-transient model failure classification.
- [x] Already-read correction for failed, unrelated, and no-requirement docs.
- [x] Ingest/Match node re-entry idempotency and merged-proposal marker.
- [x] Real child-process kill/startup-resume proof.
- [x] `review_finished_at` replay guard and loopback-only network bind.

### One ask stated in two documents becomes one row (branch `match-within-batch-duplicates`)

Written before the register became four cells. `In writing?` is now
`Written down` and `First seen` no longer exists; what this branch built about
merging and about `Written down` still stands.

- [x] Match may match a requirement against an earlier requirement of the same
      batch, answered as `same_as_requirement_index`. A confident within-batch
      match creates no second row and raises no separate question; an uncertain
      one raises a possible-match decision between the two proposed rows.
- [x] `_settle_against_the_register` downgrades a confident `existing row` only
      when the candidate is a **committed** row, so the Delivery Owner is still
      asked before this batch's evidence reaches the register.
- [x] Five refusals on the requirement path: `new row` naming either candidate,
      a match naming both, a match naming neither, a batch index that points
      forward, and a batch index outside the batch. They live on the requirement
      path, not in the helper the observation path shares.
- [x] A match may name a requirement that created no row of its own; the chain
      is followed to the row at its end rather than the answer being refused.
- [x] The merged row keeps the earlier requirement's `What was asked`, cites
      every requirement on it, recomputes `In writing?` across them, and takes
      the **earliest** document date as `First seen`
      (`app/register/document_dates.py`).
- [x] `Written down` is answered against every client requirements document
      the **project** has read, not this run's batch. The wording and the
      writer both moved on 2026-08-23: the cell reads `Not mentioned` and the
      absence move writes it at Commit, with the file as evidence.
- [x] The three outcome words are a `Literal` on both `MatchOutcome` and
      `ObservationOutcome`; the outcome-membership branch they shared is gone,
      and a test holds the `Literal` and the three constants in step.
- [x] `_merge_approved_matches` resolves its candidate through
      `merged_into_register_row_id` first, so two merges of one batch settling
      in either order cannot strand evidence on a row Commit never commits.
- [x] The Match prompt locked with Aditya on 2026-08-16, pasted word for word.
- [x] No migration was needed.
- [x] Reviewed by Codex (`-s read-only`, CLI `0.147.0`,
      `handoff/review-report-batch-duplicates.md`): **not merge-ready**, three
      findings (two P1, one P2). Every one was re-checked against the code in
      the foreground and all three were real; Aditya chose to fix all three.
      Both suites were re-run in the foreground too, because Codex's sandbox
      has no Docker socket and its verdict is code-level only.
- [x] Review findings repaired in the foreground, on the same branch, tests
      first. **An approved merge now brings the surviving row's cells up to the
      evidence it just gained** — `In writing?` stops denying a requirements
      document the row now cites, `First seen` takes the earlier of the two
      dates, the replaced cell's old citation goes with its old value, and an
      already-committed row gets its before-and-after audit entry with its
      fingerprint moved. This **reverses the slice-1 rule** that a merge moved
      citations and never a cell; the superseded wording and the narrower
      alternative that was rejected are in `DECISIONS.md`'s Git history.
      **A merge marker is never two hops from the row holding the evidence** —
      each merge re-points every row already merged into its proposal, because
      `read_findings.py` resolves exactly one hop and a two-hop chain would
      report a finding against a row Commit never commits.
      **An unplaceable document date no longer hands the row a later one** —
      where any date on a row cannot be placed, read order is kept, which is
      what the recorded limitation always said.
- [x] Tests written before those fixes:
      `test_an_approved_merge_leaves_no_cell_denying_the_row_s_own_evidence`
      and `test_a_merge_into_a_row_that_is_itself_merged_leaves_no_two_hop_marker`
      (`tests/register/test_merge_lands_on_one_row.py`), plus six unit cases in
      `tests/register/test_merge_leaves_no_contradiction.py`. At the pre-fix
      state neither file could be collected — the constants they are written
      against did not exist there — which is a weaker result than an assertion
      failure and is recorded as what it is. The date defect itself was proved
      directly against the pre-fix code, which chose the 12 March document over
      a "sometime in March" one read before it.
- [x] `test_a_second_run_over_the_intake_portal_corpus_touches_only_what_arrived`
      was changed because the behaviour it locked was deliberately reversed,
      not because it was failing awkwardly: it now asserts that the merge moves
      `In writing?` and the fingerprint, and that every other cell is untouched.
- [x] **195 Python and 44 front-end tests pass** with no live API key, both
      counts read from the suites' own printed summary in the foreground.

### Rules and findings slice (branch `rules-and-findings`)

- [x] `audit.event_kind`, nullable `cell_name`, and the conditional cell check.
- [x] `findings` table, plus `rules_snapshot`, `rules_fingerprint` and
      `examined_row_count` on `runs`.
- [x] Rules parsed and frozen at the run's first stage; an unusable file fails
      the run at the boundary and is never read as "no rules".
- [x] Examine between Match and Review: one model call for the whole register,
      safe to re-enter after a crash.
- [x] D1 and D2 computed in code; R1–R4 judged by the model.
- [x] Findings gated through the existing review queue; a rejected one stays in
      the run record and never reaches the export.
- [x] Attachment audit event naming no cell, and findings in both exports.

### Incremental update slice (branch `incremental-update`)

- [x] Seven never-do tests written and run at the baseline commit before any
      implementation; three failed there, four passed as regression guards.
- [x] Byte-identical unchanged-row proof, comparing stored cells, citations and
      fingerprints rather than what a screen renders.
- [x] Watched folder in `app/runs/watch_source_folders.py`, starting runs
      through the same `start_or_queue_run` the endpoint calls.
- [x] Rules-only route: Ingest straight to Examine when only the rules changed.
- [x] Both corpora driven through a first and a second run inside the suite.
- [x] Withdrawal, built here (migrations `20260814_0007`/`0008`), was removed
      2026-08-15 on `read-each-document-once` — see that entry below.

### Requirement withdrawal removed; a document is read once, by name or content (branch `read-each-document-once`)

- [x] Never-do tests written and run at the `main` baseline `826534e` before
      any implementation; editing and renaming an already-read document both
      failed there, four others passed as regression guards. Full detail is
      in this file's Git history, 2026-08-15.
- [x] `app/ingest/collect_batch.py`'s already-read check: `AND` to a
      parenthesised `OR`, with a skip reason naming which of name or content
      matched. `app/register/withdraw_rows.py` deleted; its two routing-edge
      conditions in `app/graph/register_graph.py` removed, the rules-only
      route untouched; every other withdrawal symbol removed with its call
      site and grepped afterward.
- [x] Migration `20260814_0011` proven forward and backward by hand on a real
      database holding an approved withdrawal from the pre-removal codebase.
- [x] Both corpora hand-driven through all four cases: first run, a new
      document, an edited document, a renamed document.
- [x] `tests/register/test_withdrawal.py` deleted outright — the one deletion
      this phase authorises. One corpus test and its supporting fixtures
      deleted too, their premise no longer possible.
- [x] 127 Python tests (was 129) and 27 front-end tests (unchanged) pass with
      no live API key.

### The screen becomes projects, and inside each project its runs (branch `front-end-projects-and-runs`)

- [x] **The status rename and its migration, proven first, in isolation, before
      anything else started** (the brief's own ordering, because a missed
      literal in a partial unique index breaks the project lock without
      failing any test): `app/runs/statuses.py`'s four values renamed;
      migration `20260815_0012` narrows `ck_runs_status` and rebuilds both
      `uq_runs_one_active_per_project` and `uq_runs_one_waiting_per_project`,
      whose `postgresql_where` clauses named the old statuses as literals.
      Proven forward and backward by hand against real PostgreSQL, seeded
      with one run in each of the four old statuses: `alembic upgrade head`
      renamed every row and rebuilt the check constraint and both index
      predicates (confirmed via `pg_get_constraintdef`/`pg_indexes`);
      inserting a second `needs review` or a second `queued` run on the same
      project then raised `UniqueViolation` against the rebuilt indexes by
      name; `alembic downgrade` restored the exact prior shape; a second
      `alembic upgrade head` re-applied cleanly. The rename's ~74 literal
      occurrences across `tests/`, `ui/tests/` and `ui/src/` were updated by a
      scripted find/replace, which corrupted three lines of plain English
      that happened to contain "waiting for review" as prose rather than the
      status value (a prompt-injection fixture sentence, a `wait_until`
      description, and a code comment) — caught by the first post-rename test
      run and hand-corrected.
- [x] `GET /projects` and MCP tool `list_projects` replace `GET /runs` and
      `list_runs` (removed, not kept beside), both calling
      `app/projects/list_projects.py`'s one core function: every project with
      its runs nested (run number, status, `started_at` — never substituted
      with `created_at` — stage, waiting-decision count, finished stages, row
      count once exported), plus the projects root and the folders inside it.
      Endpoint and MCP tool counts both stay at seven.
      `test_the_project_list_and_the_list_projects_tool_return_identical_payloads`
      proves the HTTP and MCP doors byte-identical.
- [x] Every sentence in the brief's screen-messages table rewritten at its
      named source (never in the front end): `app/projects/create_project.py`,
      `app/ingest/collect_batch.py`/`read_pdf.py`/`read_docx.py`/
      `read_source_document.py`, `app/extract/read_document.py`,
      `app/graph/register_graph.py` (including the new three-way early-exit
      split — no files at all, files found but all skipped, documents read
      but nothing stated a requirement), `app/model/client.py`,
      `app/model/call_failure.py`, `app/runs/run_lifecycle.py`. Where a
      message doubled as the log line, the log keeps the old detailed
      wording and the screen-facing value is now the terse one — never the
      other way round.
- [x] The screen rebuilt as three columns: `ui/src/ProjectList.jsx` (new),
      `ui/src/RunColumn.jsx` (new, with the collapse control), `ui/src/
      AddProject.jsx` (new, replaces `StartRun.jsx`, carries over its retry
      and disabled-button behaviour unchanged), `ui/src/StageMarks.jsx` (new,
      the compact six-mark strip shared by a project card and a run row).
      `ui/src/RunList.jsx` and `ui/src/StartRun.jsx` deleted.
      `ui/src/run_requests.js`: `readRuns` → `readProjects`; the
      network-unreachable message rewritten and marked `unreachable: true`,
      distinct from a reachable refusal, so screen 11's strip and a normal
      per-panel refusal never fire off the same signal.
      `ui/src/Stages.jsx`: the three identifier lines (run/project/status)
      removed; stage words renamed `pending`/`not needed`.
      `ui/src/Register.jsx`: export header drops the run id and formats the
      timestamp for a reader; citation cells named by heading, not
      `snake_case`; rules listed without ids as `·` bullets, a rule's own
      parameters folded into its sentence (`config/rules.yaml`'s R3 text
      edited to carry the word "days" so the fold reads "beyond 14 days",
      not "beyond 14" — the one config edit this work needed beyond what the
      brief named); heading reads "N rules ran against M rows".
      `ui/src/Question.jsx`: a finding decision renders as three labelled
      parts (Rule / Row N breaks it / Evidence) and never a rule code — which
      needed `decisions_of_run` (`app/review/review_queue.py`) extended to
      join `findings` and `register_rows` for `rule_text`/`row_number`/
      `issue`/`evidence`, since the flat `question` sentence embeds the rule
      code and can't be split safely. `ui/src/Refusal.jsx`: optional
      `heading` prop, so the Add-project box shows "Could not create this
      project" instead of "the server refused".
- [x] `config/projects.yaml` (new): `projects_root: sample-projects`, and its
      entry in `config/README.md`.
- [x] All 14 never-do tests named in the brief: 7 Python
      (`tests/projects/test_list_projects.py` new file for 4 of them;
      `tests/runs/test_finished_stages.py` and `tests/interfaces/
      test_mcp_tools.py` adapted for 2; `tests/runs/test_same_project_queue.py`
      and `tests/infrastructure/test_schema.py`'s existing lock tests
      confirmed still passing and still exercising the real partial unique
      indexes, not a Python-side check) and 7 front-end (4 new files; 3
      renamed/rewritten onto the new components — `never_offers_the_start_
      form_in_place_of_a_refusal` became `never_offers_the_add_project_box_
      in_place_of_a_refusal`, testing that the box is not offered at all
      while unconfirmed rather than testing it is hidden, since L8 makes the
      button unconditional; `never_invents_its_own_reason_for_refusing_to_
      start` rewritten because L9 (locked the same day) reverses the
      original file's premise — the screen may now refuse an empty name or
      folder in its own words, which the old test asserted it must never do).
- [x] Two new backend fields not named in the brief's file list, both
      required by a locked screen mockup and added with their own tests: a
      finding decision's `rule_text`/`row_number`/`issue`/`evidence`
      (screen 4's three-part display), and a run's `stage`/`row_count`
      alongside its `status` (L4's stage strip on a live project card, L6's
      row count on an exported run row).
- [x] Hand-driven against the real application (`docker compose`, no live
      model key; a scripted client for the scenarios needing one): the
      Add-project box's dropdown listing exactly `sample-projects/`'s two
      real folders, choosing one deriving the name, a real `POST /projects`
      succeeding while `POST /runs` refused for the missing key under
      "Could not create this project", a retry repeating only `POST /runs`;
      the runs column collapsed and expanded; the application stopped
      mid-poll showing "CANNOT REACH THE APPLICATION" over project cards
      that stayed on screen, then recovering once restarted; the project
      lock live — `POST /runs` twice in a row on one project returned
      `"status":"running"` then `"status":"queued"`; a finding's three-part
      display, a rule's folded parameter ("beyond 14 days"), the "6 rules
      ran against 1 row" heading, a `failed` run's exact screen-6 text, a
      `no changes` run's "No files were found in this folder.", and the
      export header's "Project name · exported 15 Aug, 19:35" — all matched
      the brief's locked wording exactly, once a day-month date-order bug
      caught during this pass (`toLocaleString`'s locale-dependent ordering
      gave "Aug 15" in this environment; replaced with a fixed `format_date.js`
      helper, `ui/src/ProjectList.jsx`/`RunColumn.jsx`/`Register.jsx`) was
      fixed. Screen 1's exact zero-project state and the never-do test for
      an empty-but-existing folder's "No files were found" sentence were
      not separately hand-driven (the demo project always seeds at startup,
      so a truly empty project list cannot be reached by hand in this
      environment) but are proven by the message living correctly in
      `app/graph/register_graph.py` and by the general Screen 1 "no runs"
      sub-state being confirmed both by hand and by the front-end suite.
- [x] Reviewed by Codex (`-s read-only`, CLI `0.147.0`,
      `handoff/review-report-front-end-projects-and-runs.md`): **not
      merge-ready**, one P1 and eight P2/P3 findings, none fixed by the
      implementer per protocol (a fix after review would make the reviewed
      and merged code diverge). P1: `openRun` (`ReviewScreen.jsx`) does not
      clear `run`/`exported` when switching runs, so stale decisions/buttons
      can briefly target the newly selected run's id before the new read
      lands. P2s: `ui/demo/serve_demo_runs.js` still serves the old flat
      `/runs` list and has no `/projects` route, so `/demo` no longer loads
      (a pre-existing gap, already named as a limitation, but Codex is right
      that the README's demo claim needs qualifying); `waiting` (decisions
      badge/count) is not scoped to a run at review, so L5 is violated
      outside the project card; a network failure during an answer/finish/
      create-project action sets a per-panel refusal instead of routing
      through the same `unreachable` signal as the poll, so screen 11's
      single-strip rule does not hold for actions; the screen-6 three-line
      shape and the 403/401 second line are one concatenated string, not
      structurally three lines; `read_document.py`'s dropped-quote sentence
      interpolates `{kind}`, so a dropped testing-observation/blocker does
      not end in "...this requirement was dropped" as the locked sentence
      requires; the unrelated-document skip has no separate detailed
      `log_reason` (unlike the other two rewritten skip reasons in the same
      file); the live status marks use `text-signal-edge` (dark) rather than
      `text-signal` (lime); the Add-project helper line states the "never
      creates one" explanation L8 says needs none. P3: `DECISIONS.md` still
      says `Question` has "no branch on gate kind", which is now false since
      it branches on `finding`. Reviewed against `a85b431`, code-level only —
      Codex's sandbox has no Docker socket, so it could not run either
      suite, the migration, or a browser; its own report says so. The
      migration predicates/downgrade, endpoint/tool counts, shared core
      functions, status rename, absence of a status-label map, and the L9
      test supersession all independently confirmed as shown, not claimed.
- [x] 131 Python tests (was 127) and 32 front-end tests (was 27) pass
      without a live API key.
- [x] Review findings repaired in the foreground, on the same branch, after
      Aditya decided each one. Fixed: the P1 (`openRun` now clears the run,
      its export and both refusals, so the previous run's decisions never sit
      beside buttons that act on the newly opened one); the decisions badge
      counts only a run the server reports at review; an action that never
      reached the application raises screen 11's strip instead of a per-panel
      refusal, in `ReviewScreen` and in `AddProject`, and does **not** re-read
      afterwards — a re-read would clear the strip a moment after raising it;
      the unrelated-document skip regained its detailed log line; the two live
      marks and the loading line use the locked colours; `DECISIONS.md`'s
      `Question` sentence and the README's demo paragraph now say what is
      true. Deliberately not fixed, each decided by Aditya: the screen-6
      cause and restart notice stay one string (the words are right, only the
      line break is missing); the dropped-quote sentence keeps naming the kind
      that was actually dropped, which is more honest than the locked wording
      and supersedes it; `ui/demo/` is left stale and the README now says so.
- [x] Three tests written before those fixes and run against the branch as it
      stood: all three failed there —
      `never_shows_the_previous_runs_decisions_after_opening_another_run`,
      `the_decisions_tab_counts_only_a_run_the_server_says_is_at_review`, and
      `never_calls_an_unreachable_application_a_refusal`. 35 front-end tests
      (was 32) and 131 Python tests pass after the repair, both with no key.

### A folder is a project, and the register moves to the project (branch `folder-is-a-project-and-register-moves`)

- [x] **Never-do tests written and run at `main`'s baseline `a436393` before
      any implementation**, per the brief's protocol: 7 Python
      (`tests/projects/test_create_project.py` new, 5 tests;
      `tests/register/test_review_question_wording.py` new, 2 tests) and 5
      front-end (all new files). All 12 failed at that baseline — none
      passed there, so none is a false regression guard. Full per-test
      baseline results are in the scratchpad report referenced below.
- [x] `create_project` (`app/projects/create_project.py`) rewritten as
      get-or-create: takes only `source_folder_path`, returns
      `CreatedProject(project_id, created)`; a `UniqueViolation` from a
      concurrent creator (HTTP, MCP and the startup demo seed all reach this
      function independently) is caught and re-read rather than failed. The
      name is derived from the folder's last path segment
      (dashes/underscores → spaces, each word capitalised) and is never
      accepted as input anywhere. `_confined_folder` refuses an absolute
      path or one containing `..` outright, then requires the resolved path
      to sit directly inside the resolved projects root — not the root
      itself, not nested two levels down, and a symlink leaving the root is
      caught by `Path.resolve()`. `app/projects/list_projects.py` gained
      `read_projects_root`, shared by both the dropdown's folder list and
      the confinement check, so they can never disagree about where the
      root actually is.
- [x] `POST /projects` and the MCP `create_project` tool both lost `name`;
      their answer gained `created`. `app/main.py`'s `ensure_demo_project`
      call is now one `create_project` call for
      `sample-projects/intake-portal` — the project-specific "does a row
      named X exist" check it used is gone, get-or-create alone makes a
      restart safe. Endpoint and MCP tool counts stay at seven.
- [x] Migration `20260815_0013` adds `uq_projects_source_folder_path`;
      proven forward and backward by hand against a real database: seeded
      two projects over one folder before the migration existed (schema at
      `20260815_0012`), `alembic upgrade head` refused, naming both project
      ids and the folder, and the transaction rolled back (`alembic
      current` still read `20260815_0012`, no constraint present); resolved
      the duplicate; `alembic upgrade head` then succeeded and the
      constraint was confirmed present via `pg_constraint`; `alembic
      downgrade -1` dropped it (confirmed absent); `alembic upgrade head`
      re-applied cleanly.
- [x] The register moved from a run's own tab to the project's own panel.
      `ui/src/RunColumn.jsx` gained a `Register` entry above a project's
      runs, showing the row count of the newest exported run if any.
      Opening it (`ReviewScreen.jsx`'s new `openRegister`) clears whatever
      run was open — its export and both refusals — the same clearing rule
      `openRun` already followed. A run panel now has three tabs (Stages,
      Skipped, Decisions); `ui/src/Register.jsx` is reused unchanged for the
      project panel. No new endpoint, no new core function: the panel reads
      `GET /projects` (runs newest first, `row_count` non-null once
      exported) to find the most recent exported run, then
      `GET /runs/{id}/export` for its register. Before any run has
      exported, the panel reads exactly "Nothing has been added to this
      register yet." — never an empty table.
- [x] The review question's wording changed from "Export the
      Requirements-to-Delivery Register for {name}, with {n} row(s)
      proposed by this run?" to "Add this run's changes to the register?"
      (`app/graph/register_graph.py`) — no row count, so a rules-only run
      (zero proposed rows, examining the whole register under changed
      rules) still asks the same question. (The gate itself became one press
      and `export rejected` became `discarded` on the
      `gate-becomes-one-button` branch; `runs.export_json` and
      `GET /runs/{id}/export` are still unchanged.)
- [x] **A real bug found and fixed outside the brief's scope, while wiring
      the register panel's polling:** `readRegisterFromServer` initially
      depended on the `projects` array directly. Since `GET /projects`
      answers with a new array reference every poll, and the polling
      `useEffect` depends on this callback, each poll tore the interval down
      and rebuilt it — which re-ran `readProjectsFromServer()` immediately,
      producing yet another new array, rebuilding the callback again. This
      surfaced as a genuine front-end test failure
      (`never_calls_an_unreachable_application_a_refusal` hung, and
      `never_shows_the_previous_runs_decisions_after_opening_another_run`'s
      cleared-decisions assertion failed) before the cause was traced. Fixed
      by reading `projects` through a ref updated during render, so
      `readRegisterFromServer` depends only on the cheap, navigation-driven
      primitives `registerOpen` and `selectedProjectId` (mirroring how
      `readFromServer` already depends only on `runId`). The two tests above
      are the regression guard; both pass now.
- [x] ~22 existing Python test files (every one that created a project by
      name over a `tmp_path` folder) converted onto a new
      `temporary_project_folder` helper (`tests/runs/application.py`), which
      creates a real, uniquely-named folder directly inside the repository's
      actual `sample-projects/` and removes it afterward — `tmp_path` is
      never inside the configured projects root, so the new confinement
      rule would otherwise refuse every one of them. A "waiting"/staging
      folder that is never itself sent to `POST /projects` (e.g.
      `test_watched_folder.py`, `test_incremental_updates.py`) was left
      under `tmp_path`, unchanged. `tests/interfaces/test_mcp_tools.py`'s
      `project["name"] == "..."` lookup (now meaningless — names are
      derived) was changed to match on `source_folder_path`. Done by a
      background sub-agent given a precise, example-driven brief; every
      file independently spot-checked afterward.
- [x] Three UI test files that opened a run's old `Register` tab
      (`shows_every_citation_with_its_source.test.jsx`,
      `never_calls_a_running_run_finished.test.jsx`,
      `offers_only_contract_actions.test.jsx`) rewritten to open the
      project's register panel instead. Three files that rendered
      `AddProject` directly and typed into its removed name field
      (`never_invents_its_own_reason_for_refusing_to_start.test.jsx`,
      `never_creates_a_second_project_when_only_the_run_failed.test.jsx`,
      `never_starts_a_second_run_while_the_first_is_being_opened.test.jsx`)
      had that step removed and gained the now-required `projects` prop;
      the first file's empty-name sub-test (a rule that no longer exists)
      was deleted rather than kept failing. `never_shows_a_project_the_
      server_has_not_confirmed.test.jsx`'s premise (typing a fake name,
      proving it never renders) had nothing left to substitute 1:1 once the
      field was gone, so it was simplified to prove the same L5 principle
      through the project's own server-confirmed name instead.
- [x] Hand-driven against the real application (`docker compose`, scripted
      model client, no live key): the Add-project dropdown showing only
      folders without a project and losing them one by one as projects were
      created; "No folder left to add." once all three were taken; `POST
      /projects` twice for one folder returning the same `project_id` with
      `"created": false` the second time, and `projects` holding exactly one
      row per folder; `..`, `/` and `/workspace` each refused by name; a
      project's Register panel reading "Nothing has been added to this
      register yet." before any export and the full table (cells,
      citations, rules and findings) after one; opening a run's Decisions
      tab and then that project's Register leaving no trace of the run's
      decisions or its Approve/Reject buttons; and the review question
      reading exactly "Add this run's changes to the register?" No
      screenshot or log captured a secret.
- [x] 141 Python tests (was 131) and 41 front-end tests (was 32) pass
      without a live API key — both counts read from the suites' own
      printed summary lines, not claimed from memory.
- [x] Reviewed by Codex (`-s read-only`, `handoff/review-report-folder-is-a-
      project.md`): **not merge-ready**, 7 findings (2 high, 2 medium, 3
      low). Every one was independently re-checked against the code in the
      foreground and all 7 were real; both suites were re-run in the
      foreground as well, because Codex's sandbox has no Docker socket and
      its verdict is code-level only.
- [x] Review findings repaired in the foreground, on the same branch, after
      Aditya decided each one, tests first. Fixed: the folder is now stored
      as the single path it resolves to, so `sample-projects/x`,
      `sample-projects/./x` and `sample-projects/x/` reach one project
      instead of three; `config/projects.yaml`'s `projects_root` must be
      relative and an absolute one is refused where the file is read, because
      the dropdown would otherwise advertise absolute folders that creation
      always rejects; the register panel distinguishes "not read yet" from
      "read, and there is nothing", so a project the server already reported
      as holding rows no longer shows an empty register while
      `GET /runs/{id}/export` is in flight, and the poll reads the project
      list before the register that depends on it rather than a snapshot one
      interval old; a `POST /projects` that created nothing answers `200`
      rather than `201`; eleven test helpers lost their dead `project_name`
      parameter along with every argument passed to it, and
      `ui/src/Section.jsx`'s comment no longer claims five fixed sections.
      Deliberately not fixed, each decided by Aditya: folder confinement is
      still checked only at creation (nothing but `create_project` writes
      that column, so no unconfined path can reach the database), and a
      folder named only with dashes still derives an empty project name.
- [x] Three tests written before those fixes and run against the branch as
      it stood: `test_two_spellings_of_one_folder_reach_the_same_project`,
      `test_a_call_that_created_nothing_answers_200_not_201`,
      `test_an_absolute_projects_root_is_refused_naming_the_fix`, plus the
      front-end `never_calls_a_register_empty_before_it_has_been_read`.

### Five defects found while walking the flow (branch `defects-found-while-walking-the-flow`)

- [x] `append_skipped` reconciles against what the run has already recorded
      instead of appending unconditionally, so a stage LangGraph replays from
      its start on resume no longer records the same skipped file twice. The
      comparison is over the whole entry, every key, so two different
      requirements dropped from one file — which share `kind`, `file` and
      `reason` and differ only in `summary` and `quote` — are never collapsed
      into one (`test_a_replayed_stage_does_not_record_the_same_not_used_file_
      twice`, `test_two_different_dropped_quotes_from_one_file_are_both_kept`).
- [x] `locate_quote` finds every occurrence of a quote and names every place
      it sits, in document order, instead of citing the first offset as if it
      were the only one — a repeated line is ordinary in a testing feedback
      document restating one finding against several requirements
      (`test_a_quote_appearing_under_two_headings_names_both_places`,
      `test_a_quote_appearing_once_still_names_that_one_place`).
- [x] `locate_quote` also normalises curly quotes, en/em dashes and the
      `fi`/`fl` ligatures to their plain equivalents before matching — the
      same rendering-difference tolerance whitespace already had, not the
      similarity matching the design refuses. Case is deliberately not
      normalised. The offset map keeps a one-character-to-two-character
      replacement aligned, and the citation still quotes the document's own
      characters, never the normalised ones
      (`test_a_curly_apostrophe_in_the_document_matches_a_straight_one_in_the_
      quote`, `test_a_ligature_in_a_pdf_does_not_shift_the_place_the_citation_
      names`, `test_the_citation_keeps_the_documents_own_characters_not_the_
      normalised_ones`).
- [x] A dropped quote's entry carries `file`, the same key the other Skipped
      entries already use, and the screen tells it apart from a whole skipped
      document by the presence of `summary` rather than by `file` alone, so
      it is never shown as though the file itself was never read
      (`test_a_dropped_quote_names_the_file_and_what_was_dropped`,
      `test_a_dropped_quote_is_never_shown_as_a_file_that_was_not_read`).
- [x] `read_pdf` guards pdfplumber's own parsing failure the way
      `pdf_page_count` already guards pypdf's, so a PDF sound enough to have
      its pages counted but whose content stream cannot be parsed is skipped
      with its reason instead of failing the whole run. Reproduced with a
      fabricated fixture (a font object overwritten with same-length garbage):
      pypdf still counts its one page, pdfplumber raises its own
      `PdfminerException`
      (`test_a_pdf_that_cannot_be_parsed_is_not_read_and_the_batch_continues`).
- [x] All five defects' tests were written and run at the baseline commit
      `38ec73b` before their fix; each failed there, except the ligature
      offset test, which is a regression guard and already passed. 148 Python
      tests (was 141) and 43 front-end tests (was 41) pass with no live API
      key — both counts read from the suites' own printed summary.
- [x] Reviewed by Codex (`-s read-only`, CLI `0.147.0`,
      `handoff/review-report-defects-walking-the-flow.md`): **merge-ready**,
      zero findings — the four priority hunts (offset alignment, the
      whole-entry comparison, the dropped-quote/unread-file distinction, and
      the PDF guard's exception type) and the four Definition-of-done failure
      modes all came back clean. Codex could not run either suite (no Docker
      socket in its sandbox), so its verdict is code-level only; both suites
      were run in the foreground independently, as recorded above.

### Reliability slice (branch `reliability-proof`)

- [x] Five never-do tests written and run at the baseline commit `bb24476`
      before any other work; all five passed there, so the slice is proof and
      the production code is unchanged.
- [x] Two projects run at once over one database, shown live together by both a
      polled status and the model-call timestamps, with a negative control
      confirming the timestamp check reports no overlap when the same two
      projects run one after the other.
- [x] Same-project queue: one waiting run however often a run is asked for, its
      batch formed when it starts, and picked up whether the run ahead ended
      `done` or `failed`.
- [x] The demo document's buried instruction driven through a real run and
      proven to create no row, change no cell, raise no gated proposal and
      reach no export.

### React slice (branch `react-review-screen`)

- [x] Five never-do tests written and run before any implementation; all five
      failed at the baseline on the screen module not existing.
- [x] One page, five sections in the locked order, each showing only fields
      `GET /runs/{id}` and `GET /runs/{id}/export` return. Superseded by the
      2026-08-14 redesign: a run list, four sections behind tabs, and no cost
      and timing.
- [x] One `Question` component for every gate kind, with no branch on kind.
- [x] An answer is posted and then read back: no click reaches the screen, and
      a refused answer leaves the decision unanswered with the server's reason.
- [x] Approve and Reject are offered only while the server reports the run at
      review, and the two buttons that end the review only once no decision is
      unanswered.
- [x] Polling at the interval in `ui/config/screen.json`; no websocket, no
      blocking spinner.
- [x] `/ui` served by FastAPI from `ui/dist`, answering `503` with the build
      command when the screen has not been built.
- [x] Review fix: a refused read and a refused answer are held apart, so a
      refusal about one run cannot sit beside another run's confirmed data,
      and a live refusal is not wiped by the next poll. The `503` message now
      says to restart the application, because a screen built after startup is
      not served by reloading the page.

### Operations slice (branch `operations-timing-cost`)

- [x] Six never-do tests written and run at the baseline commit `ae7a13e`
      before any implementation; all six failed there, five on
      `KeyError: 'cost_and_timing'` and one on `KeyError: 'seconds'`, and the
      two front-end cases failed on the section that said the API reported
      nothing.
- [x] Stage durations written where each pass ends, keyed by the unit of work,
      so a re-entered node replaces its own entry instead of adding one.
- [x] Token counts read off the reply in one place, `app/model/call_the_model.py`,
      and recorded against the stage that made the call.
- [x] The estimate from the rates in `config/model.yaml`, stored in
      `runs.estimated_cost_usd`, with a reason stored where there is no figure.
- [x] Migration `20260814_0009`: `token_usage`, `cost_unknown_reason`, and a
      nullable cost, because zero could not be told from unknown.
- [x] One block reported by `read_run_status`, so the endpoint, the MCP tool
      and the screen all show the same thing.
- [x] Both corpora driven end to end through export with the numbers recorded,
      and one kill-and-resume run showing nothing doubled.

### `finished_stages`, the timing/cost removal, and `GET /runs` (branch `finished-stages-and-list-runs`)

- [x] The brief's six Python and two front-end never-do tests were written and
      run at the baseline commit `d4c9eab` before any implementation. Five of
      the six Python tests share one file and failed together on
      `ModuleNotFoundError: No module named 'app.runs.finished_stages'`; the
      sixth (the MCP/HTTP identical-payload test) failed on
      `GET /runs` answering `405 Method Not Allowed` and `list_runs` being an
      unknown tool. Of the front end's cases, five passed as regression
      guards and four failed, including a literal reproduction of the "1 Jan"
      bug `new Date(null)` causes.
- [x] `runs.finished_stages` (migration `20260814_0010`), a jsonb object keyed
      by stage name and written with the same `||` merge `stage_timings` used,
      replaces `stage_timings`, `token_usage`, `estimated_cost_usd` and
      `cost_unknown_reason`, all dropped in the same migration.
      `app/runs/finished_stages.py` replaces `app/runs/cost_and_timing.py`
      with two functions: one that records a stage's mark, one that reads the
      stored object back as an ordered list of stage names.
- [x] Review's finished mark moved to the second of its two call sites in
      `app/graph/register_graph.py`, after `review_finished_at` is set, so a
      run still waiting for the Delivery Owner never reports Review finished.
- [x] The token-usage plumbing removed end to end: `ReportedUsage` and
      `ModelAnswer` out of `app/model/call_the_model.py` (it now returns the
      reply text directly); `read_one_document`, `match_requirements` and
      `examine_register` return just their answer; `CostRates`/`read_cost_rates`
      out of `app/model/client.py`; the scripted client's `usage_metadata` out;
      `rates_usd_per_token` out of `config/model.yaml`.
- [x] `GET /runs` and the MCP tool `list_runs` (D14/D15) share one core
      function, `app/runs/list_runs.py`, returning `{"runs": [...]}` — newest
      first, no cap, `started_at` sent as `null` rather than substituted with
      `created_at` for a run that has not started.
- [x] `ui/src/Stages.jsx`'s precedence bug fixed: the run's own stage now wins
      over a reported "done" only while the run is active (`running` or
      `needs review`), so a `done` run no longer shows its last stage as
      permanently "working".
- [x] `ui/src/RunList.jsx` gets an explicit `started_at === null` check ahead
      of `new Date(...)`, because `new Date(null)` is the 1970 epoch in
      JavaScript, not `Invalid Date` — the existing `Number.isNaN` guard did
      not catch it.
- [x] `tests/runs/test_timing_and_cost.py` and one test in
      `tests/infrastructure/test_schema.py` deleted outright: both proved
      behaviour of the columns this work drops, not a weakening of either test.
- [x] Assumption made beyond the brief's explicit list: two pre-existing tests
      hardcoded a stale MCP tool count of six (`test_withdrawal.py`'s
      `test_a_withdrawal_is_answered_through_the_same_six_mcp_tools`, and
      `test_schema.py`'s now-deleted cost/usage-column test) — found by a
      repository-wide grep, not the brief, and updated to match the seven
      tools this work locks in D15.
- [x] 129 Python tests and 20 front-end tests pass with no live API key.

### MCP slice (branch `mcp-tools`)

- [x] Every existence check, refusal and reported shape moved out of the routes
      into core, including the one examine block the status door and the export
      had each been building for themselves.
- [x] An MCP server mounted at `/mcp` in the application process, sharing its
      connection pool and run engine.
- [x] Six tools, no seventh: each validates its input and calls the one core
      function its endpoint calls.
- [x] A core refusal reaches a tool caller with its cause and its practical fix
      unchanged, never as an empty success.
- [x] One whole run — create, start, poll, decide, finish review, export —
      driven through the tools with no HTTP endpoint call in between.

### Formats and types slice (branch `formats-and-types`)

- [x] PDF, DOCX and plain-text readers behind one format dispatch.
- [x] Document type as a Pydantic enum; an invented type skips that document.
- [x] Related additional read and labelled but never a row on its own.
- [x] Page limit lowered to 20 and enforced in the dispatch.
- [x] Per-format citation places: PDF page, Markdown heading, DOCX/TXT line.
- [x] Reader text carries no invented characters, and a damaged PDF or Word
      file is skipped with its reason instead of ending the batch.
- [x] Both synthetic corpora written, with the binaries generated from a
      committed script.

## In progress / next slices

Nothing is in progress. Every planned slice is built and merged (the review
screen redesign landed as PR #15). What remains is the open fresh-clone and
image-only verification, and the first live-model run.

Later-slice absence is not a defect in Slice 1. Each capability becomes a
working claim only after its own implementation and proof land.

## Active blockers

1. **The export gate does not show a merge into a committed row, so removing
   the confident-match downgrade is not safe to build.** Locked as item 9 on
   2026-08-16 on the understanding that it does. Checked on 2026-08-17 by
   driving a real two-run merge: `GET /runs/{id}` at `needs review` answers
   with `run_id`, `project_id`, `status`, `stage`, `not_used`,
   `reported_instructions`, `ended_early_reason`, `failure_reason`,
   `decisions`, `examine`, `finished_stages` and `exported` — no proposed row,
   no cell, no citation. `build_export` does carry `rows[].cells` and
   `rows[].citations`, but only `WHERE is_committed`, and it is built inside
   Commit, after the gate is answered; `GET /runs/{id}/export` answered `409`
   before approval. Removing only the downgrade would in fact change nothing:
   `_the_candidate_to_ask_about` raises the possible-match decision whenever the
   answer names a committed row, whatever the outcome, so the question would
   still be asked and an approval would still merge. Making the merge automatic
   needs three things together — stop raising the question, perform the merge
   without a decision, and show the merge at the gate.
   **Decided 2026-08-17: the downgrade stays and the gate is not widened.** The
   demo is driven in pairs, where the question never arises at all; the cost of
   the one-per-run order is written up under `## Known limitations`.
   **Still open after 2026-08-18.** The gate is now one press
   (`gate-becomes-one-button`), which changed when the decision is written and
   not what it shows: the buttons carry no preview of what will change, and
   whether they should is the question that remains here. The register
   becoming a live read (`register-read-live`) changes nothing here either:
   `build_export` is now `build_register_document`, the run-level export
   route is gone, and the register read still serves committed rows only, so
   the gate still shows no merge.
2. **Development Compose mount is too broad for final proof.** `.:/workspace`
   is intentionally retained for iteration, exposes local `.env`, and lets
   local files override the image. Remove/narrow it and wipe stale dev DB
   before final image-only/fresh-clone verification.

## Active assumptions and unverified claims

| Assumption / claim | Current basis | What closes it |
|---|---|---|
| Register stays around 15 rows/~250 tokens | Basis for no embedding shortlist | Run the Helpline AI corpus end to end |
| Source documents are usually 5–10 pages | Small-team domain expectation | Measure actual corpora; revisit pgvector/chunking only if needed |
| Real SDK exception classification matches tests | Typed `status_code`; only scripted/401 path observed | Live provider failure evidence |
| SDK retry is close enough to locked policy | Two attempts/120s configured; SDK owns wait | Live timing and explicit retry evidence |
| Default OpenRouter model is suitable | Configured but never called | Bounded live-model run |
| The Helpline AI end-state table (`sample-documents/helpline-ai/README.md`) — 7 row statuses, 3 rule findings, 1 rule expected silent | Written from the brief's design against the corpus text; never run | The bounded live-model run over the staged Helpline AI corpus |

## Known limitations

- **An unanswered possible match is examined as the match it asks about**, so
  a rejected match leaves the new row without a finding for that run. Written
  up for a reader in README's "What it does not do"; the next run raises it.
- **A model-judged rule that runs again may not re-raise an earlier finding.**
  The register shows the newer answer and History keeps the older one; README's
  "What it does not do" states it for a reader.
- **A rule still asks its question again on every run**, once the documents it
  names have been read — README's "What it does not do" is that one's home.
  `applies_when` removed the worse half of it: the demo's six findings raised
  before any testing feedback existed.
- **A handover only ever sets `Handed over`; `Partial` stays testing's word**
  (decided 2026-08-23, item 36) — README's "What it does not do" is the home.
- **A rule never runs against an observation that reached no row** (S10): it
  is shown on the Skipped tab instead — README's "What it does not do" is the
  home.
- **A file dropped into a brand-new project's folder before the watcher's
  first look at it starts no run by itself.** The watcher's first sight of a
  project records whatever the folder holds as the baseline, and that first
  sight lands at its next poll — up to `poll_seconds` after the project is
  created. A file landing in that window (after the creation-time run
  collected its batch, before the baseline is taken) waits for the next run,
  whichever way it starts; it is never lost, because a batch collects every
  file not yet read. Decided 2026-08-18 with Aditya: shrink the window by
  config (`poll_seconds` 4 → 2, `quiet_seconds` 10 → 5 on 2026-08-23; first
  10 → 4 and 30 → 10) rather than persist
  a creation-time folder baseline, which would take a migration; revisit only
  if a live run or demo actually hits the window.
- **Rules about elapsed time cannot be judged.** "Nothing stays blocked more
  than N days" has nothing to count from: the register keeps no document dates,
  and Extract no longer asks for one.
- **Work stopped by something outside the provider's control is reported
  through the source document, not through a cell of its own.** The register
  can no longer say that a requirement is waiting on the client.
- **A batch holding two documents of one type is read in file-name order
  between them.** This is not rare — both corpora hold two meeting notes, so
  the fallback fires on every full batch. It is harmless while the two state
  different asks, which is the case in both corpora, and undecided if they ever
  state the same one.
- **A violation that persists across runs raises its question again on every
  run.** Examine judges the whole register each run — necessary, because a
  rule verdict follows the row's current cells (a row failing "every written
  requirement must have a testing outcome" stops failing it the moment the
  testing feedback arrives), so no row is ever "already examined" for good.
  The cost is not compute (one register-sized call either way) but noise: a
  row that stays in violation is re-found, and the person is asked the same
  question run after run. Decided 2026-08-18 with Aditya: leave the design,
  watch this in the bounded live-model run; if question spam is real there,
  the fix is a small dedup in `record_findings` — same rule, same row with an
  unchanged fingerprint, already answered → raise no new question — never
  hiding rows from Examine. **Watched in the live run 2026-08-19 and real**:
  every staged drive re-asked the testing-outcome rule on each run — six or
  seven questions per run early on, settling to two once the testing feedback
  arrived. Each was rejected and each returned. The dedup is now a real option
  rather than a guess, and is still not built.
- **A finding's `evidence` is never checked against the row it names.** Examine
  refuses an answer naming a rule or a row it was not given, but the `evidence`
  string is only checked for being non-empty — nothing looks for those words in
  the row's four cells. A model that paraphrases instead of quoting therefore
  puts its own sentence on the review screen and in the export under "Evidence".
  Unlike Extract, where `locate_quote` drops a quote it cannot find in the
  document, nothing here verifies the copy. **Decided 2026-08-17 not to add the
  check**: rejecting the whole answer over one imperfect copy is worse than the
  fault, and this is to be closed by strengthening the Examine prompt instead.
  **Seen in the live run 2026-08-19, in its mild form.** The three drives
  wrote three distinct evidence strings: two were the row's own cell word for
  word, and the third read "no testing outcome has been read" where the cell
  reads "Not known yet — no testing outcome has been read for this
  requirement." Nothing false reached the screen, but nothing checked the copy
  either — which is the fault this entry names.
- **A confident match against a committed row still raises a question, one per
  overlapping ask.** It appears only when documents arrive one per run: the
  meeting note's asks are committed by the first run, so every ask the client
  requirements document restates in the second is a match against a committed
  row, and each raises its own question. In the intake-portal corpus that is
  **one** question, because only the email notification is stated in both
  documents; on an engagement whose requirements document writes down most of
  the meeting, it would be one per row, which is the noise that trains a
  reviewer to approve without reading. **Arriving in pairs or all at once raises
  none of them**, because nothing inside one batch is committed — that is why
  the demo is driven in pairs. A confirmation is not a contradiction and the
  brief asks only for the second; removing the question is blocker 1 and was
  deliberately not built.
- **A handover read after testing has already moved a row sends that row back
  to `Handed over`, and drops the testing citation with it.** `status_after`
  asks only whether *this batch* holds testing, never whether testing has ever
  spoken. Unreachable in all three supported arrival orders and in both corpora,
  each of which holds one handover and one testing document: it needs a handover
  arriving in a batch later than the testing that already moved that row.
  Found by the 2026-08-17 review and left deliberately.
- **`Status` can keep a testing citation the cell's own value denies.** The
  verdict being superseded is read off `What testing found`, and `Change
  request` and `Unclear` move that cell without moving `Status`, so the two
  diverge. It takes three testing documents across three runs with a change
  request in the middle; neither corpus holds a second testing document. Found
  by the same review and left deliberately.
- **A document that lands a row on the status it already holds adds no
  citation**, because a move whose value is unchanged is skipped before its
  citations are settled. This is the one place the "every supporting citation,
  no cap" rule does not hold. It needs a second handover, or a second testing
  document repeating the first's verdict — neither corpus has one.
- **Only the requirements half of a batch is ordered by document type.** Testing
  observations and delivery evidence are still gathered in file-name order. No
  status depends on it, since a status is decided from the set of labels; it
  shows only in the order two testing documents' sentences are joined into
  `What testing found`.
- **A row stored before migration `20260817_0017` keeps a fingerprint computed
  over seven cells** until something moves that row. Nothing in the application
  compares a stored fingerprint with a recomputed one, so no behaviour depends
  on it, and a comparison across runs still answers "unchanged" correctly; what
  is wrong is that the export publishes a number that will not verify against
  the four cells printed beside it. A fresh database never holds such a row.
  Recomputing inside the migration was considered and refused: a migration that
  computes a hash has to carry the application's rules.
- The 20-page limit binds `.pdf` only; Markdown reports no page count and none
  is invented for it.
- A handover summary that lists requirements, in a run that never exports, is
  not counted as already read, so the next run reads and pays for it again. A
  handover summary that lists none is unaffected.
- One Extract call may repeat in the answer-to-checkpoint kill window.
- A run that fails is not restarted by itself, and nothing it read counts as
  read — the next run started on that project reads its documents again.
- A document not read rather than read (too long, encrypted, wrong format, a
  failed model call) is never written to `documents`, so it is not "already
  read" either; the next run attempts it again, paying again if a model call
  was what failed.
- A rejected finding stays suppressed if later evidence strengthens it.
- A finding already approved onto a row is not re-examined by a later run; a
  rules change is applied the next time a run examines that register.
- The rule "no register row is `Done` without a testing outcome", which lived in
  code as `D2` until 2026-08-17 and now lives in `config/rules.yaml`, still
  needs a seeded row to produce: a `Passed` observation sets a row `Done` and
  fills `What testing found` in the same move, so the two cannot ordinarily
  disagree. `D1` ("every register row cites a source") is deleted rather than
  moved — a row without a citation cannot be created, and `commit_register`
  refuses one outright, which is stronger than a finding.
- The elapsed-time rule that needed a document date left with the date cells on
  2026-08-17. Of the rules that remain, **none has been confirmed firing in a
  run**: no run has been driven that leaves a written requirement without a
  testing outcome and watched Examine raise the finding. No surviving rule's
  text or parameters changed.
- Files arriving during Review wait; that run holds the project lock, and the
  watcher starts nothing behind it.
- The watcher keeps what it last saw in memory, so restarting the application
  re-baselines every folder: a file that arrived while it was down starts no run
  of its own and is read by the next run started by hand.
- Whatever the watcher first sees in a folder is not an arrival, so a project
  created over a folder of documents is read by `POST /runs`, not by itself.
- A document is read once per project, for its whole lifetime, matched by name
  or by content. Deleting, renaming, or editing an already-read document does
  nothing; a requirement a document no longer asks for keeps its row. See
  README's "What this does not do, and why" for the full boundary and the
  workflow answer (save an edited document under a new name to have the
  revision read).
- The screen is built by Node, which the application image does not carry, and
  `.dockerignore` excludes `ui/`, so `ui/dist` must be built on the host before
  `docker compose up`; the bind mount is what carries it into the container.
  Image-only serving is part of the open fresh-clone verification.
  **Superseded on 2026-08-25:** the pinned Node stage now builds `ui/dist` and
  copies it into the Python image; the no-bind image proof serves the screen.
- The screen authenticates nobody, exactly as the endpoints behind it do not.
- A folder that exists but the application cannot read is accepted by
  `create_project`, which only checks that it is a directory; the failure
  appears later inside Ingest as an `OSError` per file.
- A run waiting for review holds its project's lock until a person answers
  it. There is no timeout and no way to abandon a run, so a review left
  unanswered stops that project from starting another run. This is
  deliberate: expiring a review would be the system deciding on the
  person's behalf.
- The race in `app/runs/run_lifecycle.py:85-92`: when a run is running and
  another is queued, a third request can find both inserts refused and then
  find the queued run already promoted, so `already_waiting` is `None` and
  the caller gets a `TypeError` and a 500 with no sentence instead of a
  refusal. Deliberately not fixed — the fix is small but an honest test for
  it is not, and the window needs three concurrent requests on one project.
  Named here so nobody reports it as new.
- The screen polls `GET /projects` and `GET /runs/{id}` unconditionally, on a
  fixed interval, whatever is on screen and whatever a run's status is
  (L1, locked 2026-08-15) — there is no per-project runs endpoint and no
  conditional refresh.
- Run events below `WARNING` reach nothing when the application is started the
  way the Dockerfile starts it. uvicorn's shipped logging configuration leaves
  the `register.run` logger without a handler, so `log_run_event` at INFO is
  dropped by the root logger's last-resort handler and only WARNING and ERROR
  events reach stderr. The records themselves are correct and each carries its
  `run_id`; what is missing is the sink D16 describes. The reliability tests
  supply their own logging configuration to read them.
- Neither door authenticates a caller; the MCP endpoint additionally answers
  `421` to a `Host` header other than `localhost` or `127.0.0.1`, so a client
  on another machine cannot reach it as it stands.
- Fresh-clone and image-only verification remain open.

## Next actions

1. Consolidate the repository's documentation before the write-up — the two
   decision files and the two progress files are more than a reader of a
   one-page write-up and an architecture diagram needs. Not yet decided what
   is kept.
2. Clear the throwaway state the live run left: `.gitignore:49` is widened to
   `sample-projects/*/`, seventeen drive folders sit under `sample-projects/`,
   and the `helplinelive` stack still holds fifteen projects of drive data.
   The stack is deliberately left up until the demo recording is done.

Resolved 2026-08-19: the live-model run is made, and the testing it was for is
complete — three staged drives (Luna single and Terra single through MCP, Luna
combo through the screen), each reaching all seven expected statuses. See
`## Verification evidence`. The full drive-by-drive record is kept at
`documentation/superdocs-engineering-task/live-run-record.md` as raw material
for the Task 4 write-up, and is meant to be deleted once that write-up exists.

Resolved 2026-08-18: the export-gate item is closed — the downgrade stays and
the gate is not widened, decided 2026-08-17 and recorded under `## Active
blockers`; the gate-preview half was decided out of the one-press-gate brief
the same day.

Resolved 2026-08-18: the already-read question is decided and built — an
unrelated document settles whatever its run did, but a no-requirement
document (testing feedback, a handover) of a discarded or failed run is read
again, the same rule requirement-bearing documents follow.
`test_a_testing_document_read_only_by_a_discarded_run_is_read_again` failed
at the baseline (the third run never reached review — the file was settled
for ever) and passes with the narrowed clause.

Resolved 2026-08-18: the run logger now owns a stdout handler, configured
once at startup — `tests/runs/test_run_events_reach_stdout.py` proves the
JSON line reaches stdout with its `run_id`, exactly once even if startup
configures twice. Before the change an INFO run event printed nothing
(demonstrated by hand at the baseline: captured stdout was empty).

## Verification evidence

| Evidence | Last confirmed | Result / boundary |
|---|---|---|
| The live model run, staged by hand | 2026-08-19, `main` at `7720623` | Three drives on the Helpline AI corpus, `openai/gpt-5.6-luna` and `openai/gpt-5.6-terra` at `reasoning_effort: high`. Each reached **all seven expected statuses**, including `Disputed` on the human-escalation row, whose audit trail reads `Nothing said yet` → `Handed over` → `Disputed` across three separate runs (that first status is the wording of the day; migration `20260823_0022` renamed it `Requested` on the rows, and an audit entry already written keeps the words it was written with) — the cross-batch conflict PR #38 fixed, confirmed on live data rather than in tests alone. Luna raised the written-requirement finding on that row and Terra never did; the two agreed on every status. The change-request rule raised no finding in any drive: the SMS ask is reported as a dropped observation, because no row traces it. **A merged fix is not live until the application process restarts** — the first drive returned six of seven against modules the container had imported before PR #38 reached disk |
| `docker compose -p helplinelive exec -T app pytest` | 2026-08-20, `main` at `69ecaec` | **253 passed**, real PostgreSQL, no live key, run inside the live stack |
| `npm --prefix ui test` | 2026-08-20, `main` at `69ecaec` | **66 passed across 38 files**, no live key. The baseline printed 63 across 36; the three new tests cover the read-only wording and the decision card's shared label column, and all three fail at the branch point |
| `docker compose -p brief5live run --rm app pytest` | 2026-08-18, `register-read-live` branch | **235 passed**, real PostgreSQL, no live key. The baseline at `f6aa015` printed 227; the eight new tests are the two read-once tests, the four live-register tests and the two both-doors register tests |
| `npm --prefix ui test` | 2026-08-18, `register-read-live` branch | **60 passed, 34 files**, no live key. Same counts as the baseline — the register tests were updated in place to the one-GET register route and the rows-empty state |
| Migration `20260818_0021` forward and backward on real data | 2026-08-18, `register-read-live` branch | On a scratch database at `20260818_0020`: `pg_get_constraintdef` over `pg_constraint` for `runs` showed only `ck_runs_status`, the FK and the PK; `pg_indexes` only the PK and the two partial unique indexes on `project_id`/`status`; no view exists — nothing names `export_json`. A seeded `done` run held a snapshot; the upgrade dropped the column and left the run intact; the downgrade re-added it `jsonb`, nullable, with the seeded run's snapshot NULL (empty, not reconstructed); upgrading again dropped it once more |
| The live register driven by hand | 2026-08-18, `register-read-live` branch | One throwaway project under `sample-projects`, deleted after, scripted client, no key, buttons pressed in a real browser. Run 1 committed one row; the Register panel showed the live table — "1 row", "last updated" from the run's `finished_at`, cells, citation, rules. Run 2 over the unchanged folder ended `no changes` with the document `not_used` kind `already read`. A second document arrived; run 3 reached review and was ended with the Discard button — register unchanged, still 1 row, same timestamp. The watcher then auto-started run 4, which **read the discarded run's document again** (second Extract call in the log), and adding it moved the live panel to 2 rows with a new `last updated`; the queued run 5 then ended `no changes` with everything already read |
| `docker compose -p brief3gate run --rm app pytest` | 2026-08-18, `gate-becomes-one-button` branch | **224 passed**, real PostgreSQL, no live key. The baseline at `963c3a7` printed 216; the eight new tests are the two migration tests, the four one-press tests and the two both-doors tests, all written and seen failing first |
| `npm --prefix ui test` | 2026-08-18, `gate-becomes-one-button` branch | **57 passed, 33 files**, no live key. The baseline printed 53 across 32 files; the new file covers the gate never rendering as a question, the body each ending press sends, and a `discarded` run showing `discarded` |
| Migration `20260817_0019` forward and backward on real data | 2026-08-18, `gate-becomes-one-button` branch | Seeded at `20260817_0018` with one run per status, each on its own project, including `export rejected`. Before the step, `pg_get_constraintdef` showed `ck_runs_status` naming `export rejected` and `pg_indexes` showed both partial unique indexes naming only `running`/`needs review` and `queued` — so no index needed rebuilding. The upgrade rewrote exactly that one run to `discarded` and recreated the constraint with the new value; inserting `export rejected` afterwards was refused by `ck_runs_status` and `discarded` was accepted; the downgrade restored both the rows and the old constraint; upgrading again reached the same shape |
| Both presses driven by hand against the live stack | 2026-08-18, `gate-becomes-one-button` branch | Two throwaway projects under `sample-projects`, deleted after the run, with the scripted client and no key. Each run reached `needs review` carrying only its own finding — no export decision. Finishing with no body answered `400` naming the body to send; finishing with the finding unanswered answered `409` naming that decision. After approving it, `{"add_to_register": true}` answered `200 review finished`, the run reached `done`, the export held the one row with its approved finding, and the recorded export decision read `Add this run's changes to the register?` / `approved`. On the second project `{"add_to_register": false}` answered `200`, the run reached `discarded`, `exported` stayed false, `GET /runs/{id}/export` answered `409`, and `GET /projects` listed the two runs as `done` with 1 row and `discarded` with none |
| `docker compose -p brief2wording run --rm app pytest` | 2026-08-17, `wording-and-prompts` branch | **214 passed**, real PostgreSQL, no live key. The baseline at `1a03ceb` printed 202; the twelve new tests are eight Match question refusals, two Examine question tests, the grouped-observation stacking test, and a re-run of the fixtures the required field touched |
| `docker compose -p fgbrief2 run --rm app pytest` | 2026-08-17, `wording-and-prompts` branch, after the review repair | **216 passed**, real PostgreSQL, no live key. The two new tests are the blank-non-null-question refusals on both Match paths, written first and seen failing |
| `npm --prefix ui test` | 2026-08-17, `wording-and-prompts` branch | **53 passed, 32 files**, no live key. The baseline printed 47 across 31 files; the new file covers the code-owned Approve/Reject block on all three kinds of card, and two cases were added to the Reported-tab file for the notice said once and the new empty state |
| `docker compose -p fcfinal run --rm app pytest` | 2026-08-17, `register-becomes-four-cells` branch | **200 passed**, real PostgreSQL, no live key. The baseline in this worktree printed 195 |
| `npm --prefix ui test` | 2026-08-17, `register-becomes-four-cells` branch | **46 passed, 30 files**, no live key. The baseline printed 44 across 29 files; the new file covers the `Written down` heading and the four-cell row |
| Migration `20260817_0017` forward and backward on real data | 2026-08-17, `register-becomes-four-cells` branch | Seeded at `20260816_0016` with one row per status including `Blocked`, each citing all seven cells. The upgrade refused naming row `#6` and rolled back whole (constraint, columns and citations all unchanged, read from `pg_get_constraintdef` and `information_schema`). After changing that row's status the upgrade dropped the three columns, deleted their citations and narrowed the constraint to the six statuses including `Handed over`; the downgrade restored the columns and `Blocked` without refusing; upgrading again reached the same shape |
| Both corpora, two arrival orders each | 2026-08-17, `register-becomes-four-cells` branch | Intake portal one-per-run and in pairs ended with the identical five-row register; Northside Dental likewise, with `Status` on rows 1, 3 and 5 citing both `handover-summary.md` and `testing-feedback-15-jul.pdf`. The Northside corpus ran with its requirements document as `.md`. Driven by a throwaway script, deleted after the run |
| Export gate for a merge into a committed row | 2026-08-17, `register-becomes-four-cells` branch | Driven by a throwaway test, deleted after the run: at `needs review` the gate shows the two questions and nothing of the row — no cells and no citations — and `GET /runs/{id}/export` answers `409`. Recorded as blocker 1 |
| `docker compose -p batchfinal run --rm app pytest` | 2026-08-16, `match-within-batch-duplicates` branch | 188 passed, real PostgreSQL, no live key. The baseline at `2fdff45` printed 170; the 18 new tests are the eight refusal and outcome-schema tests in `tests/match/test_match_answer.py` and the ten in `tests/match/test_within_batch_duplicates.py`. Fourteen of the sixteen never-do tests were written and run at `2fdff45` first and failed there; the two that passed there are regression guards — the invented-outcome refusals and the separate-runs committed-row gate |
| `npm --prefix ui test` | 2026-08-16, `match-within-batch-duplicates` branch | 44 passed, 29 files, no live key — byte-for-byte the baseline count. No front-end file changed: a decision between two proposed rows renders through the same question the screen already shows |
| Intake-portal corpus, first run, all four documents | 2026-08-16, `match-within-batch-duplicates` branch | Five rows, not six. The email-notification ask is one row saying `Yes — written in client-requirements-v1.md.`, citing both `client-requirements-v1.md` and `meeting-notes-10-mar.md`, with `First seen` `10 March 2026` — the meeting note's date, though the requirements document was the file read first. The WhatsApp and search rows read `Not found in client-requirements-v1.md.`, and the only question raised was the export gate. Driven by a throwaway test, deleted after the run |
| Northside Dental corpus, first run, all six documents | 2026-08-16, `match-within-batch-duplicates` branch | Five rows: the meeting note's booking and daily-schedule asks landed on the requirements document's rows rather than becoming rows of their own, both with `First seen` `5 June 2026` and both files cited; the SMS reminder stayed its own row reading `Not found in client-requirements-v1.docx.`; nothing that was one row became two. Driven by a throwaway test, deleted after the run |
| `docker compose -p finished-stages run --rm app pytest` | 2026-08-14, `finished-stages-and-list-runs` branch | 129 passed, no live key |
| `docker compose -p start-a-run run --rm app pytest` | 2026-08-15, `start-a-run-from-the-screen` branch | 129 passed, no live key — no Python changed, run to confirm nothing broke |
| `npm --prefix ui test` | 2026-08-14, `finished-stages-and-list-runs` branch | 20 passed, 8 files, no live key. Two new files cover the stage-strip precedence fix and the null-`started_at` fix |
| `npm --prefix ui test` | 2026-08-15, `start-a-run-from-the-screen` branch | 27 passed, 13 files, no live key. Four new files cover L1, L3, L4 and L5 for the start-a-run form; all four were written and run against the baseline first. Two more cases were added after review found two defects those four missed — the form rendering before `GET /runs` had answered, and the button staying live through the parent's re-read, which let a second click queue a second run. Both were reproduced as failing tests before either was fixed |
| Review screen run | 2026-08-14, `react-review-screen` branch | One run driven through `/ui` in a browser: three gates answered one at a time, one finding approved and one rejected, the review finished, and the exported register read back with its citations and the approved finding only |
| Review screen polling | 2026-08-14, `react-review-screen` branch | A second run watched from `running`/`match` through to its recorded failure without a reload; Finish review was never offered and no register was shown |
| Kill-and-resume | Slice 1 | Real child process + `SIGKILL`; completed extraction not repeated |
| API flow | Slice 1 | One run driven by hand through review/export |
| Northside Dental corpus run | 2026-08-13, `formats-and-types` branch | 6 documents read across `.md`/`.docx`/`.pdf`; unrelated skipped, related additional labelled without a row; 7 rows exported |
| Intake-portal rules run | 2026-08-14, `rules-and-findings` branch | 5 rows examined against R1–R4 plus D1–D2; two R1 findings gated; `finish-review` refused while they were unanswered; one approved and one rejected; export carried the approved finding only, and row 4's fingerprint stayed the seven-cell hash |
| MCP flow | 2026-08-14, `mcp-tools` branch | One run created, started, polled, decided, finished and exported through the six tools; the export refused before approval |
| Intake-portal second run | 2026-08-14, `incremental-update` branch | Meeting notes read first, then the written scope; rows 2 and 3 byte-identical, row 1's cells and fingerprint unmoved while an approved merge added its citations, rows 4 and 6 new |
| Northside Dental second run | 2026-08-14, `incremental-update` branch | Meeting notes read first, then `.docx` scope and `.pdf` testing feedback; the SMS row byte-identical, rows 1 and 3 unmoved through their merges, rows 5 and 7 new |
| `docker compose -p read-once run --rm app pytest` | 2026-08-15, `read-each-document-once` branch | 127 passed, real PostgreSQL, no live key |
| `npm --prefix ui test` | 2026-08-15, `read-each-document-once` branch | 27 passed, 13 files, no live key — unchanged from baseline; only a comment and a demo run changed |
| Migration `20260814_0011` forward and backward on real data | 2026-08-15, `read-each-document-once` branch | Driven by hand on a database holding an approved withdrawal, produced from the pre-removal codebase: `alembic upgrade head` refused with `"1 register row(s) are 'Withdrawn' ... change its status, then run this migration again"`, rolled back cleanly (still at `20260814_0010`, the withdrawn row and its decision both intact); after changing that row's status, `alembic upgrade head` completed (column dropped, both checks narrowed, the `'withdrawal'`-kind decision deleted, no register row lost); `alembic downgrade 20260814_0010` restored the exact prior schema. Re-run independently a second time against a fresh database, because the code review could not reach a Docker socket and so could confirm this migration only by reading it; the refusal, the whole-transaction rollback and the retry all behaved identically |
| Intake-portal corpus hand-driven, all four cases | 2026-08-15, `read-each-document-once` branch | First run: 6 rows committed. New document: register grew to 7 rows, all 6 prior rows byte-identical. Edited already-read document: skipped, reason named the name matched and to save it under a new name, no new Extract call for that file. Renamed already-read document: skipped, reason named the content matched under a different name |
| Northside Dental corpus hand-driven, all four cases | 2026-08-15, `read-each-document-once` branch | Same four cases as the intake-portal run, same outcomes: first run 3 rows, new document made it 4 with the first 3 byte-identical, the edit and the rename were each skipped with the matching reason and no new model call |
| Watched folder | 2026-08-14, `incremental-update` branch | An arriving file started a run by itself; a second file arriving during that run's review started nothing until the review finished |
| Two projects at once | 2026-08-14, `reliability-proof` branch | Both runs live together — polled as `running` with a stage set, and two model calls started less than the 2-second call delay apart; rows, citations, decisions, findings and log lines each stayed with the run that produced them |
| Same-project queue | 2026-08-14, `reliability-proof` branch | One waiting run across four requests; its batch held only the file that arrived after it was queued; it started by itself after a `done` run and after a `failed` one |
| Buried instruction | 2026-08-14, `reliability-proof` branch | `meeting-notes-20-mar.md` read in a real run: the line stored and logged as an embedded instruction, one register row from the other document, the export gate the only question asked, and the export refused until it was approved |
| New tests repeated | 2026-08-14, `reliability-proof` branch | Five runs in a row, five passes; no sleep added anywhere |
| Redesigned screen | 2026-08-14, `review-screen-redesign` branch | Four demo runs driven through it in a browser — at review, working, failed, exported — with gates answered and the accent clearing as they were. Against `ui/demo/` only; the screen has not been driven against the application since the redesign |
| Rules-only run reports no Extract/Match | 2026-08-14, `finished-stages-and-list-runs` branch | A second run on a project whose rules changed and no document arrived: `finished_stages` read `["ingest", "examine"]` mid-review and `["ingest", "examine", "review", "commit"]` once done — never `extract` or `match` |
| `GET /runs` and `list_runs` identical | 2026-08-14, `finished-stages-and-list-runs` branch | One run driven to Review; `GET /runs` and the MCP tool `list_runs` returned byte-identical payloads |
| Start-a-run form | 2026-08-15, `start-a-run-from-the-screen` branch | Hand-driven in a browser against the application: an empty database showed the form; a folder that does not exist and a blank name were each refused with `create_project`'s own sentence, word for word, and nothing was created; a real folder (`sample-projects/northside-dental`) created its project (`POST /projects` 201) while the environment's empty `OPENROUTER_API_KEY` refused the run start (`POST /runs` 503); a second click retried only `POST /runs` — the `projects` table held exactly one row for it throughout. A run could not be watched through Ingest onward this way, because there is no live model key here |
| Demo runs after this change | 2026-08-15, `start-a-run-from-the-screen` branch | `npm --prefix ui run dev`, all four demo runs (`demo-review`, `demo-running`, `demo-failed`, `demo-exported`) still listed and opened correctly; `ui/demo/serve_demo_runs.js` was not changed — it has no write path for `POST /projects` or `POST /runs`, but its run list is never empty, so the start-a-run form never renders against it and the gap does not show |
| `docker compose -p folder-verify run --rm app pytest` | 2026-08-16, `folder-is-a-project-and-register-moves` branch | 138 passed, real PostgreSQL, no live key |
| `npm --prefix ui test` | 2026-08-16, `folder-is-a-project-and-register-moves` branch | 40 passed, 25 files, no live key |
| `docker compose -p fixfolder3 run --rm app pytest` | 2026-08-16, same branch, after the review repairs | 141 passed, real PostgreSQL, no live key. Re-run in the foreground, independently of the implementing agent, because Codex cannot reach a Docker socket |
| `npm --prefix ui test` | 2026-08-16, same branch, after the review repairs | 41 passed, 26 files, no live key |
| Migration `20260815_0013` forward and backward on real data | 2026-08-16, `folder-is-a-project-and-register-moves` branch | Seeded two projects over one folder at revision `20260815_0012`; `alembic upgrade head` refused, naming both project ids and the folder, transaction rolled back (`alembic current` still `20260815_0012`, constraint absent via `pg_constraint`); duplicate resolved by hand; `alembic upgrade head` then succeeded and the constraint was confirmed present; `alembic downgrade -1` dropped it (confirmed absent); `alembic upgrade head` re-applied cleanly |
| Folder-is-a-project hand-driven | 2026-08-16, `folder-is-a-project-and-register-moves` branch | Real application, scripted model, browser: Add-project dropdown listed all three unclaimed folders, then two, then showed "No folder left to add." once all three had projects; the demo project's derived name read "Intake Portal"; a new project's derived name read "Hand Drive Check" from `sample-projects/hand-drive-check`; `POST /projects` twice for one folder returned the same `project_id` with `"created": false` the second time and `projects` held exactly one row per folder (confirmed by direct query); `..`, `/` and `/workspace` were each refused by name over HTTP, no row added by any of the three |
| Register-moves hand-driven | 2026-08-16, `folder-is-a-project-and-register-moves` branch | Same session: a project that had never run read "Nothing has been added to this register yet."; a run driven to Review showed the question "Add this run's changes to the register?" verbatim; after approving and finishing, its project's Register entry read "1 row" and opening it showed the full table with citations and rules; opening the run's own Decisions tab (showing the answered export decision) and then clicking Register left no trace of the run's decision or its Approve/Reject buttons on screen |
| `docker compose -p fx8 run --rm app pytest` | 2026-08-16, `match-within-batch-duplicates` branch, after the review repairs | 195 passed, real PostgreSQL, no live key. Was 188 before the three repairs; the seven new tests cover the merge recompute, the merge chain and the date ordering. Re-run in the foreground, independently of the implementing agent, because Codex cannot reach a Docker socket |
| `npm --prefix ui test` | 2026-08-16, same branch, after the review repairs | 44 passed, 29 files, no live key — unchanged; no front-end file was touched |
| Live model | Never | Unverified |
| Fresh clone/image-only | Not run yet | Open release gate |

## Documentation history policy

- Current status is rewritten here; completed dated narrative is dropped once
  it stops describing the present, and stays reachable in this file's Git
  history.
- Never repeat decision rationale here; link to the current decision instead.
- When a blocker resolves, record its resolution and evidence here briefly,
  then drop it from the active list once nothing depends on it.
