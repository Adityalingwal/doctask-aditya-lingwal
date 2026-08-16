# PROGRESS.md — current project dashboard

Current status only. Detailed dated narrative is archived in
[`documentation/progress-history.md`](documentation/progress-history.md); the
exact pre-compaction source is
[`documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`](documentation/archive/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md).
Decision rationale belongs in `DECISIONS.md`, not here.

## Snapshot — 2026-08-17, branch `register-becomes-four-cells`

Built, and each item run rather than type-checked. Every decision below was
locked with Aditya on 2026-08-16; the superseded wording is in
`documentation/decision-history.md`, "the register becomes four cells".

- **The row is four cells** — `What was asked` · `Written down?` ·
  `What testing found` · `Status`. `Blocked on`, `First seen` and `Last moved`
  are gone, with `app/register/document_dates.py`, Extract's `document_date`
  and `blockers` lists, rule `R3`, and the `Blocked` status. The stored column
  behind `Written down?` is still `in_writing`.
- **`Handed over` replaces `Blocked` in the status check constraint.** A
  handover summary with no testing behind it moves the row there, so the third
  of four runs finally does something visible.
- **A batch is read in workflow order** — meeting notes → client requirements →
  handover summary → testing feedback — so which statement of an ask creates a
  row is a fact about the documents, not about their file names.
- **`Status` keeps every citation that still supports it.** The handover's
  citation survives the move to `Done`; a superseded testing verdict does not.
- **No rule is judged outside `config/rules.yaml`.** D1 deleted, D2 moved in as
  `R5`, `app/examine/deliverable_checks.py` gone.
- **Two formats, not four.** `.md` and `.pdf` are kept; `.docx` and `.txt`
  leave with `app/ingest/read_docx.py`, `python-docx`, their tests and their
  two written limitations. `sample-projects/northside-dental/client-requirements-v1.docx`
  is now `.md`.
- **The fourth document type is named `handover summary`.**

**Not built, and it is a blocker for Aditya rather than a defect:** removing the
downgrade of a confident match against a committed row. That decision rests on
the export gate showing such a merge, and the gate does not — see
`## Active blockers`.

## Completed

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
  export and the screen head the cell `Written down?` while the stored column
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
- [x] `failed`, `no changes`, `export rejected` semantics.
- [x] Configuration-vs-transient model failure classification.
- [x] Already-read correction for failed, unrelated, and no-requirement docs.
- [x] Ingest/Match node re-entry idempotency and merged-proposal marker.
- [x] Real child-process kill/startup-resume proof.
- [x] `review_finished_at` replay guard and loopback-only network bind.

### One ask stated in two documents becomes one row (branch `match-within-batch-duplicates`)

Written before the register became four cells. `In writing?` is now
`Written down?` and `First seen` no longer exists; what this branch built about
merging and about `Written down?` still stands.

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
- [x] `In writing?` reads `Not found in <file>.` once the **project** has read a
      client requirements document that does not mention the ask; the query
      joins `documents` to `runs`, so an earlier run's document is visible.
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
      citations and never a cell; `documentation/decision-history.md` carries
      the superseded wording and the narrower alternative that was rejected.
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
      rules) still asks the same question. The gate itself, `runs.status`'s
      `export rejected`, and `runs.export_json`/`GET /runs/{id}/export` are
      unchanged in behaviour.
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
      into one (`test_a_replayed_stage_does_not_record_the_same_skipped_file_
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
      (`test_a_pdf_that_cannot_be_parsed_is_skipped_and_the_batch_continues`).
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

1. **The export gate does not show a merge into a committed row, so removing
   the confident-match downgrade is not safe to build.** Locked as item 9 on
   2026-08-16 on the understanding that it does. Checked on 2026-08-17 by
   driving a real two-run merge: `GET /runs/{id}` at `needs review` answers
   with `run_id`, `project_id`, `status`, `stage`, `skipped`,
   `reported_instructions`, `ended_early_reason`, `failure_reason`,
   `decisions`, `examine`, `finished_stages` and `exported` — no proposed row,
   no cell, no citation. `build_export` does carry `rows[].cells` and
   `rows[].citations`, but only `WHERE is_committed`, and it is built inside
   Commit, after the gate is answered; `GET /runs/{id}/export` answered `409`
   before approval. `_merge_approved_matches` is driven only by an approved
   possible-match decision, so with the downgrade removed nothing would perform
   the merge at all and the proposal would be committed as a second row for the
   same ask. **Aditya decides**: leave the downgrade, or widen the gate first.
2. **Development Compose mount is too broad for final proof.** `.:/workspace`
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

- `Disputed` is reached only when the handover and the testing feedback that
  contradict each other are read in the **same batch**. `status_after` decides
  it from the delivery evidence this batch supplied, and nothing stores the
  fact that a handover once claimed delivery — so a handover read in an earlier
  run leaves a later "not there" verdict landing on `Not delivered` instead.
  Closing it needs a stored claim on the row, not a wider read.
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
- A committed row keeps the `Written down?` sentence it was committed with, so a
  row committed before any client requirements document was read still says
  "no client requirements document has been read for this project" after one
  arrives. Rewriting rows a new document did not affect is exactly what the
  system must not do; closing this needs a decided rule about which cells a
  later document may re-answer.
- The 20-page limit binds `.pdf` only; Markdown reports no page count and none
  is invented for it.
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
- D1 and D2 were driven against seeded rows: every proposed row is written with
  a `what_was_asked` citation, so D1 has nothing to catch. D2 ("no row is `Done`
  without a testing outcome") is reachable from 2026-08-16 — a `Passed`
  observation now sets a row `Done` and fills `what_testing_found` in the same
  move, so a `Done` row without an outcome still needs seeding to produce.
- R3 and R4 in `config/rules.yaml` could not fire before 2026-08-16, because
  `what_testing_found` and `blocked_on` were constants. Both now move. **Not
  yet confirmed by a run**: no run has been driven that leaves a row blocked
  past `max_days`, or written without a testing outcome, and watched Examine
  raise the finding. Neither rule's text or parameters changed.
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
- A project's register panel shows the empty line
  ("Nothing has been added to this register yet.") until that project has a
  run that has exported — a new project, a first run still working, or a
  run whose export was rejected all read the same way, since none of them
  has moved `row_count` off `null` yet.
- The screen is built by Node, which the application image does not carry, and
  `.dockerignore` excludes `ui/`, so `ui/dist` must be built on the host before
  `docker compose up`; the bind mount is what carries it into the container.
  Image-only serving is part of the open fresh-clone verification.
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

1. Decide what to do about the export gate and the confident-match downgrade
   (blocker 1).
2. Decide whether one bounded live-model run is worth making.
3. Decide whether the run logger should be given its own stdout handler, so the
   INFO run events D16 describes reach a reader outside a test.
4. Decide whether the already-read rule should settle a related additional
   document the way it settles an unrelated one.

## Verification evidence

| Evidence | Last confirmed | Result / boundary |
|---|---|---|
| `docker compose -p fcfinal run --rm app pytest` | 2026-08-17, `register-becomes-four-cells` branch | **200 passed**, real PostgreSQL, no live key. The baseline in this worktree printed 195 |
| `npm --prefix ui test` | 2026-08-17, `register-becomes-four-cells` branch | **46 passed, 30 files**, no live key. The baseline printed 44 across 29 files; the new file covers the `Written down?` heading and the four-cell row |
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

- Current status is rewritten here; completed dated narrative moves to
  `documentation/progress-history.md`, newest first.
- Never repeat decision rationale here; link to the current decision instead.
- When a blocker resolves, move its resolution and evidence to history and
  remove it from the active list.
- Exact pre-compaction hashes and inventory mapping live in the compaction
  manifest under `documentation/archive/history/`.
