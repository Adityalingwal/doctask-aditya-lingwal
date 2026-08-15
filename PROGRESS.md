# PROGRESS.md — current project dashboard

Current status only. Detailed dated narrative is archived in
[`documentation/progress-history.md`](documentation/progress-history.md); the
exact pre-compaction source is
[`documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`](documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md).
Decision rationale belongs in `DECISIONS.md`, not here.

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

## Completed

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
- [x] `failed`, `no changes`, `export rejected` semantics.
- [x] Configuration-vs-transient model failure classification.
- [x] Already-read correction for failed, unrelated, and no-requirement docs.
- [x] Ingest/Match node re-entry idempotency and merged-proposal marker.
- [x] Real child-process kill/startup-resume proof.
- [x] `review_finished_at` replay guard and loopback-only network bind.

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
      2026-08-15 on `read-each-document-once` — see that entry below and
      `documentation/decision-history.md`.

### Requirement withdrawal removed; a document is read once, by name or content (branch `read-each-document-once`)

- [x] Never-do tests written and run at the `main` baseline `826534e` before
      any implementation; editing and renaming an already-read document both
      failed there, four others passed as regression guards. Full detail:
      `documentation/progress-history.md`, 2026-08-15.
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
      run and hand-corrected; see `documentation/decision-history.md`.
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
- [x] Reviewed by Codex (`-s read-only`, CLI `0.147.0`): see this section's
      final update below for the verdict once the review returns.
- [x] 131 Python tests (was 127) and 32 front-end tests (was 27) pass
      without a live API key.

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
      review, and Finish review only once no decision is unanswered.
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

| Order | Work | Scope | Current state |
|---|---|---|---|
| 1 | Review screen redesign | Run list, section tabs, Tailwind tokens, demo server | Built on `review-screen-redesign`; documentation updated, awaiting merge |

Every planned slice is built. What remains is the open fresh-clone and
image-only verification, and the first live-model run.

Later-slice absence is not a defect in Slice 1. Each capability becomes a
working claim only after its own implementation and proof land.

## Active blockers

1. **Development Compose mount is too broad for final proof.** `.:/workspace`
   is intentionally retained for iteration, exposes local `.env`, and lets
   local files override the image. Remove/narrow it and wipe stale dev DB
   before final image-only/fresh-clone verification.

## Active assumptions and unverified claims

| Assumption / claim | Current basis | What closes it |
|---|---|---|
| Register stays around 15 rows/~250 tokens | Basis for no embedding shortlist | Run both complete synthetic projects |
| Source documents are usually 5–10 pages | Small-team domain expectation | Measure actual corpora; revisit pgvector/chunking only if needed |
| Real SDK exception classification matches tests | Typed `status_code`; only scripted/401 path observed | Live provider failure evidence |
| SDK retry is close enough to locked policy | Two attempts/120s configured; SDK owns wait | Live timing and explicit retry evidence |
| Default OpenRouter model is suitable | Configured but never called | Bounded live-model run |

## Known limitations

- The 20-page limit binds `.pdf` only; Markdown, plain text and Word report no
  page count and none is invented for them.
- A `.docx` citation names a line of the extracted text, not a line Word
  displays, so it cannot be jumped to inside Word; the quoted words are how the
  passage is found. Naming the Word heading instead needs headings to leave the
  reader without being written into the text — deferred to a later improvement,
  not refused.
- A quote spanning two `.docx` table cells is not found, because each cell is
  its own line; that requirement is dropped with its reason.
- A related additional document that lists requirements, in a run that never
  exports, is not counted as already read, so the next run reads and pays for
  it again. A related additional document that lists none is unaffected.
- One Extract call may repeat in the answer-to-checkpoint kill window.
- A run that fails is not restarted by itself, and nothing it read counts as
  read — the next run started on that project reads its documents again.
- A document skipped rather than read (too long, encrypted, wrong format, a
  failed model call) is never written to `documents`, so it is not "already
  read" either; the next run attempts it again, paying again if a model call
  was what failed.
- A rejected finding stays suppressed if later evidence strengthens it.
- A finding already approved onto a row is not re-examined by a later run; a
  rules change is applied the next time a run examines that register.
- D1 and D2 cannot fire on the register slice 1 produces: every proposed row is
  written with a `what_was_asked` citation and no stage yet sets a row to
  `Done`. Both were driven against seeded rows instead.
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
- `GET /runs/{id}` returns no register rows, so the screen's register section
  is empty until that run has exported; a run whose export was rejected never
  shows a register at all.
- The screen is built by Node, which the application image does not carry, and
  `.dockerignore` excludes `ui/`, so `ui/dist` must be built on the host before
  `docker compose up`; the bind mount is what carries it into the container.
  Image-only serving is part of the open fresh-clone verification.
- The screen authenticates nobody, exactly as the endpoints behind it do not.
- The Add-project box reads a folder inside the application's container,
  whose only mount is `.:/workspace`, so a path outside the repository is
  refused by `create_project`; this is deliberate, not fixed by widening the
  mount (`docker-compose.yml` is untouched).
- The screen polls `GET /projects` and `GET /runs/{id}` unconditionally, on a
  fixed interval, whatever is on screen and whatever a run's status is
  (L1, locked 2026-08-15) — there is no per-project runs endpoint and no
  conditional refresh.
- A reported embedded instruction reaches a person only through the run's log
  line: `GET /runs/{id}` does not carry it, and neither does the export. D02
  scenario 9 makes it information rather than a gate, and there is currently no
  surface that shows that information.
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

1. Merge `review-screen-redesign` and `finished-stages-and-list-runs`.
2. Decide whether one bounded live-model run is worth making.
3. Decide whether the run logger should be given its own stdout handler, so the
   INFO run events D16 describes reach a reader outside a test.
4. Decide whether the already-read rule should settle a related additional
   document the way it settles an unrelated one.

## Verification evidence

| Evidence | Last confirmed | Result / boundary |
|---|---|---|
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
| Live model | Never | Unverified |
| Fresh clone/image-only | Not run yet | Open release gate |

## Documentation history policy

- Current status is rewritten here; completed dated narrative moves to
  `documentation/progress-history.md`, newest first.
- Never repeat decision rationale here; link to the current decision instead.
- When a blocker resolves, move its resolution and evidence to history and
  remove it from the active list.
- Exact pre-compaction hashes and inventory mapping live in the compaction
  manifest under `documentation/archive/history/`.
