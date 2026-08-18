# Progress history

This is the detailed pre-compaction progress record frozen from `PROGRESS.md`
at commit `2e14c91` on 2026-08-13. Completed dated narrative and resolved
blockers belong here. Current status, active blockers, assumptions and next
actions live in root `PROGRESS.md`; the exact byte-for-byte source is
`documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`.

New completed entries are added newest-first below this header.

## Snapshot — 2026-08-18, branch `audit-history-read`

Built and run rather than type-checked, committed and pushed; the branch is
waiting for review and for Aditya's gates. No pull request is open.

- **The audit trail became readable.** One core function, `read_history`
  (`app/register/read_history.py`), read-only over `audit` — no migration, no
  schema change, nothing new written. Three thin doors over it:
  `GET /projects/{id}/history`, the `get_history` MCP tool, and a HISTORY
  section at the bottom of the screen's Register panel. Both counts moved
  seven → eight, which is why the two count-lock tests were updated.
- **The register document did not change by one byte** — history is a read
  of its own, and a never-do test asserts the register payload still carries
  no `history` and no `entries` key.
- **A row's birth is folded to one entry in the core function**, so curl, the
  MCP tool and the screen are answered with the same list; the both-doors
  test compares the two payloads under `json.dumps(sort_keys=True)`.
- **Hand-driven on the live stack** (compose, scripted model, no key): two
  runs over one project gave `row created` (run 1, meeting-note.md) and, above
  it, the `status` and `what_testing_found` changes (run 2,
  testing-feedback.md); the same JSON came back byte-identical through
  `get_history`, and the screen showed the section, its NOTE chip and the
  newest-first order.
- **Both suites green on this branch, no live key:** **247 Python passed**
  (baseline 239 passed / 8 failed, every failure a new test or a deliberately
  updated count) and **63 front-end passed across 36 files** (baseline 60
  passed / 3 failed). Re-run independently in the foreground after the
  review: the same **247** and **63 across 36** were printed there.
- **Codex's one finding (Medium) fixed in the foreground, on the branch,
  after Aditya decided it (2026-08-18).** Two findings attached to one row
  in one run tie on `created_at`, `row_number` and a null `cell_name`, so
  two reads could order them two ways — against the locked newest-first
  ordering. `HISTORY_QUERY` gained the final `audit.id ASC` key. The new
  test (`test_two_findings_attached_to_one_row_in_one_run_keep_one_order`)
  drives the two-attachment state and pins three consecutive reads equal;
  it **passed pre-fix too** (`1 passed` recorded) — no honest test can
  force PostgreSQL to flip a tied order on demand, so the determinism
  rests on the total ordering, stated here the same way the REPEATABLE
  READ guarantee is.

Everything below is the position this branch started from.

- **The register is read live, and the snapshot is gone.** One core function
  builds the register document from `register_rows` at read time;
  `GET /runs/{id}/export` became `GET /projects/{project_id}/register` and
  `get_export` became `get_register` (both counts still seven); Commit
  stops writing `runs.export_json` and migration `20260818_0021` drops the
  column, proven forward and backward by hand.
- **The trap went first.** `collect_batch`'s already-read rule — the
  snapshot's one non-display reader — became `runs.status = 'done'` in its
  own first commit, proven on both corpora and on a discarded run before
  anything else was touched.
- **An empty register answers the empty state**, never a 409 and never an
  error, and the header timestamp is the newest `done` run's `finished_at`.
- **Both review findings fixed on the branch, test-first (2026-08-18).**
  Codex's High: an approved finding of an at-review or discarded run was
  visible in the live register (the discarded half predated this branch —
  `build_export` used the same unfiltered query); the query now requires the
  finding's run to be `done`, and the two new tests in
  `tests/register/test_a_finding_follows_its_runs_ending.py` failed at
  baseline on exactly that leak (`2 failed`, both on the finding's issue
  text). Codex's Medium: the multi-query read now runs inside one
  `REPEATABLE READ` transaction — no honest test can force the race, so the
  guarantee rests on the isolation level, stated here rather than tested.
- **Both suites green on this branch, no live key:** **237 Python passed**
  (baseline 227; 235 before the review fixes) and **60 front-end passed
  across 34 files** (baseline 60 across 34 — existing files updated in
  place).

Details, including the recorded test-first baseline failures, are under
`## Completed` and `## Verification evidence` in root `PROGRESS.md`.

Everything before this branch — `not_used` and its kinds, the one-press
review ending, `discarded`, the four-cell row, `Handed over`, workflow
order, rules living only in `config/rules.yaml`, two formats — is in
`## Completed` under its own branch entry in root `PROGRESS.md`.

**Was not built as of this snapshot, and was a blocker for Aditya rather than
a defect:** removing the downgrade of a confident match against a committed
row. That decision rested on the export gate showing such a merge, and the
gate did not — see the `helpline-ai-corpus` snapshot and root `PROGRESS.md`
`## Active blockers` for current status.

## Resolved limitation — the register panel read empty until a run had exported (resolved 2026-08-18, branch `register-read-live`)

The limitation read: a project's register panel shows the empty line
("Nothing has been added to this register yet.") until that project has a run
that has exported — a new project, a first run still working, or a discarded
run all read the same way, since none of them has moved `row_count` off
`null` yet. It described the snapshot path: the panel walked the project's
runs for the newest exported one and fetched that run's copy. The register is
now read live from `register_rows` through
`GET /projects/{project_id}/register`, so the panel shows committed rows the
moment they exist and the empty line exactly while the project holds none —
the limitation is not narrowed but gone.

**Superseded snapshots, moved here on 2026-08-17 when the register became
four cells.** They describe the seven-cell row, four document formats and the
two deliverable checks in code, none of which is current.

## Snapshot — 2026-08-16, branch `extract-schema-and-the-delivery-half`

Built, and each item run rather than type-checked:

- **The extraction contract is a schema.** `app/model/answer_schema.py`
  generates a strict `json_schema` from the Pydantic answer model and
  `call_the_model` sends it; Extract, Match and Examine share the one helper,
  and the hand-written JSON examples are gone from all three prompts. Pydantic
  validation and `json_object_in` stay, because the scripted client returns
  plain text.
- **`app/extract/prompt.py` carries the prompt locked with Aditya on
  2026-08-16**, pasted word for word. It states judgement only: what a label
  means, what counts as a blocker, and which lists each document type may fill.
- **`delivery_evidence` is a fourth quoted list.** A handover summary reports
  what was handed over, located in the source exactly like every other quote.
- **Which lists a type may fill is enforced at the boundary, not papered over.**
  `register_graph.py`'s silent `requirements_found = 0` is gone; a filled list
  the type may not use skips that one document with a reason naming what came
  back, and the batch continues.
- **The delivery half is wired.** Testing feedback and a handover summary move
  rows and create none: `what_testing_found`, `blocked_on`, `status` and
  `last_moved` all move, with the moving document's citation. `first_seen` and
  `last_moved` finally diverge.
- **A move is proposed, never written where it is worked out.** Moves are
  stored on `runs.pending_moves`, overlaid so Examine judges the register as
  the run leaves it, and applied inside Commit's transaction after merges
  settle their targets — so a rejected export leaves the register unchanged.
  Attaching evidence to a committed row, and any uncertain link, is a new
  `observation match` question in the review queue.
- **A reported embedded instruction reaches a person**: `runs.reported_instructions`,
  `GET /runs/{id}`, both export shapes and a fourth tab on the run panel. The
  document is still read; the closing sentence saying so is on the card and in
  the Markdown export.
- **`Never happened` is renamed `Not delivered`** (migration `20260816_0014`),
  proven forward and backward by hand against a real database with a stored row
  actually holding the old value, reading `pg_get_constraintdef` rather than
  trusting the three migration files that spell the old literal out.

**Assumptions made while building this, written here rather than left in a
message:**

- **`last_moved` when two documents move one row in one batch** carries the
  date of the document read *last*, which is the one whose value the cell ends
  holding. Documents are read in file-name order, not date order, so a handover
  dated later than a testing document can leave the earlier date in the cell.
  Deterministic, and stated rather than hidden.
- **An observation matching no row is reported on the Skipped tab**, the
  reporting surface the brief left to the implementer, with a reason naming the
  kind of observation and saying it was reported rather than attached.
- **A confident link to a row this same batch proposed applies without its own
  question.** Nothing in the batch is committed and the export gate still
  covers it — the within-batch rule already locked for Match. A link to a
  *committed* row, and any uncertain link, is always asked about.
- **A moved cell's citation is replaced, not accumulated.** The old citation
  supported a value the cell no longer holds; the audit keeps the history.

### Review findings repaired in the foreground, after the review

Codex returned **not merge-ready** with two P1s, three P2s and one P3. Every
finding was re-checked against the code in the foreground and all six were
real; Aditya chose to fix all six, plus three deviations from the brief's own
protocol. The reviewed code and the merged code therefore differ, which is why
each repair is named here.

- **P1 — a `Passed` move produced a false D2 finding.**
  `register_under_examination` overlaid this run's pending cell values but not
  its pending citations, so Examine saw `status = Done` with no
  `what_testing_found` citation and reported the row as Done without a testing
  outcome — against the very evidence that moved it. Pending citations now
  travel with pending values, and
  `test_a_row_this_run_moved_to_done_raises_no_finding_about_a_missing_outcome`
  asserts what the existing delivery tests never did.
- **P1 — an undated handover matched a row and moved nothing.** The
  `last_moved` fallback fired only when another cell had already moved, and
  delivery evidence alone moves no other cell. Delivery evidence now always
  moves `last_moved`: the document's date when it has one, `date unknown` when
  it does not.
- **P2 — the stored skip reason did not name what came back.** The Skipped tab
  said only that the model reported something the type may not; the type and
  the list lived in the log line, which never reaches a screen. Both are now in
  the stored sentence, and the test that blessed the generic wording asserts
  the named one.
- **P2 — observation matching was sent a schema describing requirements.**
  `match_observations` reused `MatchAnswer`, whose descriptions say
  "requirement", and refusals reported missing "requirements" for observations.
  Observations now have `ObservationAnswer` with `observation_index` and their
  own refusal wording, plus
  `test_an_incomplete_observation_answer_is_refused`.
- **P2 — "its requirements are in the register" was not always true.** An
  embedded instruction may appear on a document that states no requirement at
  all — the backend test uses exactly such a document. The sentence stops at
  "This document was still read." The brief's §5.4 wording is superseded.
- **P3 — the canonical documents still described the old behaviour.**
  `DECISIONS.md` said an embedded instruction appears nowhere in the export and
  `PROGRESS.md` said it reached only the log; both are now true, and the
  resolved limitation is removed rather than reworded.

Three deviations from the brief's protocol were closed with them:

- **The Northside handover now runs.** `handover-summary.md` was in no batch of
  any test — not a defect, but a corpus test that copies selected files and
  never included it. It joins the second run's batch and moves three rows: the
  booking pages, the daily schedule screen, and the email reminder this same
  batch proposed. The SMS reminder row still comes back byte for byte.
- **The never-do tests were run at the baseline `927dc25`** in a worktree of
  their own. They fail there on `ImportError: cannot import name
  'OBSERVATION_PROMPT_MARKER'` — the whole delivery half does not exist at that
  commit, so the file cannot be collected. That is a weaker result than an
  assertion failure and is recorded as what it is, not dressed up.
- **`test_a_cell_moved_by_an_observation_writes_its_audit_entry_and_moves_the_fingerprint`
  is written**, and deliberately drives two runs: a row created and moved in
  one run never publicly holds `No evidence yet`, so only a second run
  exercises the move against an already-committed row — the branch the test
  exists for.

**170 Python and 44 front-end tests pass** with no live API key, both counts
read from the suites' own printed summary in the foreground.

### `Not delivered` and `Disputed` are reachable — a fifth testing label

Decided with Aditya on 2026-08-16, after the review. Both statuses need a
document to say the asked-for work is *not there*, and the four testing labels
could not express it: `Defect` is "anything testing found broken", which is the
`Partial` row of the same table, and `Change request` and `Unclear` move no
status. `TestingLabel` therefore gains a fifth value, **`Not found`** — testing
looked and the thing is not there at all — and the locked extraction prompt
gains it with a worked example from the intake-portal corpus's own testing
feedback ("The records list page opens, but there is no way to search old
records from it" is `Passed` for the page and `Not found` for the search).

`status_after` reads it against what else the batch supplied: `Not found` with a
handover claiming delivery is `Disputed`, and `Not found` with no handover
behind it is `Not delivered` — silence is not a claim, so nothing is
contradicted. The two never-do tests that waited on this are written and pass:
`test_testing_reporting_a_requirement_missing_after_a_silent_handover_is_not_delivered`
and `test_a_handover_claiming_delivery_against_testing_reporting_missing_is_disputed`.

**`Disputed` is reachable but not demonstrated on a corpus.** Neither synthetic
corpus contains a handover claiming delivery of something testing then reports
absent — Northside's testing feedback says the SMS reminder "still does not
reach the patient", which is broken rather than missing. The corpus was left
alone rather than edited to flatter the feature; the status is proven by a test,
not by a corpus run, and that difference is stated here rather than blurred.

A second, smaller gap in the same table: it names no line for "handover says
delivered, testing says nothing". A handover alone therefore moves `Last moved`
and no status, on the reasoning that a handover says the work exists and never
that it behaves as asked — which is what `Done` means. That reading is written
into D05 and can be reversed with one line if it is wrong.

## Snapshot — 2026-08-14

- Slice 1, the formats and types slice, the rules and findings slice, the MCP
  slice, the incremental update slice, the reliability slice and the React
  slice are merged into `main`.
- The operations slice is merged into `main` with its original timing and cost
  behaviour dropped from the screen only.
- On branch `finished-stages-and-list-runs`, not yet merged: `runs.finished_stages`
  is built, timing and cost are removed from the application in full (D16),
  and `GET /runs` plus its MCP tool `list_runs` are built (D14/D15) — the run
  list on the review screen now has a real endpoint to read instead of
  `ui/demo/`'s dev-only middleware. 129 Python tests and 20 front-end tests
  pass on this branch without a live API key.
- No live model call has been made; all runs/tests used the scripted client.
- Implemented pipeline: `.md`, `.pdf`, `.docx` and `.txt` Ingest → Extract →
  Match → Examine → Review → Commit.
- Implemented interface: seven FastAPI endpoints and the same seven operations
  as MCP tools mounted in the same process, startup demo-project seed, review
  queue including finding gates, JSON/Markdown export.
- Verified reliability: real-process `SIGKILL` resume, no repeated completed
  extraction, Ingest/Match re-entry safety, honest terminal statuses.
- Two projects run at once without either appearing in the other's rows,
  citations, decisions, findings or log lines, and a second run on one project
  waits until the first releases the lock.
- The demo document's buried instruction is reported as a fact about that
  document and never acted on.
- Both synthetic corpora are written: four intake-portal documents and the six
  Northside Dental documents in `.md`, `.docx` and `.pdf`.
- Rules are frozen per run, findings are gated one by one, and an approved
  finding attaches to its row without moving that row's fingerprint.
- A second run reads only files it has never read before, by name or content,
  and leaves every row an unaffected document supplied byte-identical, proven
  on both corpora against the stored rows.
- Each project's folder is watched: poll and quiet period come from
  `config/watcher.yaml`, and nothing starts behind a run that is already in
  flight.
- The review screen was rebuilt on `review-screen-redesign`: the viewport is
  split into a run list and one run's sections, read one at a time behind tabs,
  on Tailwind tokens with IBM Plex served from the repository. Nobody types a
  run id any more. Still nothing is shown that the server did not send back.
- Timing and cost are gone from the screen and, on the
  `finished-stages-and-list-runs` branch, from the rest of the application
  too (D16).
- **2026-08-15, branch `start-a-run-from-the-screen`:** the screen can now
  start a run. A `StartRun` form (project name, source folder, `Start run`)
  renders once `GET /runs` has answered with zero runs; it validates nothing
  and shows the server's own refusal unchanged. A retry after a failed
  `POST /runs` never repeats `POST /projects` (`projects.name` has no unique
  constraint). Hand-driven against the application: an empty database showed
  the form, a missing folder and a blank name were each refused word for
  word, and a real folder created its project while the environment's
  missing `OPENROUTER_API_KEY` refused the run start — a second click did
  not create a second project. 25 front-end tests (was 20) and 129 Python
  tests (unchanged) pass without a live key.
- **2026-08-15, branch `read-each-document-once`:** requirement withdrawal is
  removed, not disabled. A run now reads a document exactly once per project,
  matched by name or by content, instead of re-reading a changed one; see the
  branch's own entry under Completed and `documentation/progress-history.md`
  for the full detail, and `documentation/decision-history.md` for why.
  Migration `20260814_0011` was proven forward and backward on a real database
  holding an approved withdrawal. 127 Python tests (was 129) and 27 front-end
  tests (unchanged) pass without a live key.
- **2026-08-15, branch `front-end-projects-and-runs`:** the screen becomes
  projects, and inside each project its runs — see the branch's own entry
  under Completed for the full detail. Four run statuses are renamed
  (`waiting`→`queued`, `waiting for review`→`needs review`, `closed without
  export`→`export rejected`, `ended without changes`→`no changes`); migration
  `20260815_0012` narrows `ck_runs_status` and rebuilds both partial unique
  indexes, proven forward and backward by hand. `GET /runs` and `list_runs`
  are replaced by `GET /projects` and `list_projects` (endpoint and tool
  counts stay at seven). 131 Python tests (was 127) and 32 front-end tests
  (was 27) pass without a live key.
- **2026-08-16, branch `folder-is-a-project-and-register-moves`:** a folder is
  now a project's identity (get-or-create, unique `source_folder_path`, name
  derived and never accepted, confined to the projects root), and the
  register moved from a run's own tab to the project's own panel — see the
  branch's own entry under Completed for the full detail. Migration
  `20260815_0013` adds the unique constraint, proven forward and backward by
  hand, including the duplicate-refusal path. Endpoint and MCP tool counts
  stay at seven; no new door was added for the register. Codex reviewed it
  read-only and returned seven findings; all seven were re-checked in the
  foreground, five were repaired and two deliberately left. 141 Python tests
  (was 131) and 41 front-end tests (was 32) pass without a live key.

**2026-08-15.** Removed requirement withdrawal on `read-each-document-once`,
cut from `main` at `826534e`. Written before any implementation: never-do
tests for an edited document, a renamed document, a deleted document, an
unsure match staying gated, a document whose model call failed being read
again, and the rules-only route, run at that baseline. Editing and renaming
both failed there with a `TimeoutError` waiting for `ended without changes`,
because the pre-removal already-read check matched on name AND content, so
either kind of change was still treated as a new document; the other four
passed as regression guards. Built: `app/ingest/collect_batch.py`'s
already-read check changed one operator — `AND` to a parenthesised `OR` — so
a document already read by either its name or its content is skipped, and
the skip reason now names which of the two matched and what to do about it
(save an edited document under a new name; a renamed one needs nothing).
`app/register/withdraw_rows.py` deleted outright; `app/graph/register_graph.py`
lost the `withdraw_rows` import, `RunState`'s `reads_a_row_source_again` and
`withdrawals_proposed` fields, and the half of each of `_route_after_extract`
and `_route_after_match` that existed only for withdrawal —
`_route_after_ingest` and the rules-only route it drives were read carefully
and left untouched. `_early_reason`'s `REGISTER_UNCHANGED` string removed
with it: `app/register/propose_rows.py` inserts one proposed row per
requirement unconditionally, so once Match runs — which now only happens
when the batch found a requirement — it always has something to propose, and
that reason string had become unreachable. `STATUS_WITHDRAWN`,
`WITHDRAWAL_DECISION`, `raise_withdrawal_decision`,
`decisions.source_document_id`, and `CommitResult.withdrawn_row_numbers`
removed with their call sites; each deleted symbol was grepped across the
repository afterward to confirm nothing was left importing or asserting on
it. Migration `20260814_0011` (`down_revision = "20260814_0010"`) drops
`decisions.source_document_id` and its foreign key, deletes any
`'withdrawal'`-kind decision before narrowing `ck_decisions_kind` back to
three kinds (the same technique `20260814_0007`'s own downgrade used for that
constraint), and refuses — naming the row count, the cause, and the fix —
rather than delete or reguess a `'Withdrawn'` row's status before narrowing
`ck_register_rows_status`, the same way `20260814_0007`'s downgrade refuses
for that column. Proven by hand on a real database holding an approved
withdrawal, built from the pre-removal codebase: the forward migration
refused exactly as designed, rolled back cleanly, completed once the row's
status was changed, and the downgrade restored the prior schema exactly.
`tests/register/test_withdrawal.py` deleted outright — the one deletion this
phase authorised, the behaviour itself being deliberately removed — along
with the re-issued-scope test in `tests/incremental/test_second_run_on_corpora.py`
(its premise, a same-named file re-read on new content, can no longer occur)
and the fixtures that existed only to support it
(`sample-projects/intake-portal/second-version/`,
`write_client_requirements`). Both corpora were hand-driven through a first
run, a new document, an edited document and a renamed document, matching the
suite's own proof. `ui/src/Question.jsx` lost the word "withdrawal" from its
comment and gained no branch on gate kind (D15). `ui/demo/serve_demo_runs.js`
lost its fourth `demo-review` decision; the four demo runs stayed distinct
without it. 127 Python tests (was 129) and 27 front-end tests (unchanged)
pass with no live key. README gained one section, "What this does not do,
and why," stating the boundary once in the founder's own terms, with the
workflow answer carried in the same breath as the editing limitation.

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
