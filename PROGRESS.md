# PROGRESS.md — current project dashboard

Current status only. Detailed dated narrative is archived in
[`documentation/progress-history.md`](documentation/progress-history.md); the
exact pre-compaction source is
[`documentation/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`](documentation/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md).
Decision rationale belongs in `DECISIONS.md`, not here.

## Snapshot — 2026-08-14

- Slice 1, the formats and types slice, the rules and findings slice, the MCP
  slice and the incremental update slice are merged into `main`.
- The reliability slice is built on `reliability-proof`, not yet merged. It
  changed no production code: every test in it passed against `main` the first
  time it ran.
- 122 tests pass without a live API key.
- No live model call has been made; all runs/tests used the scripted client.
- Implemented pipeline: `.md`, `.pdf`, `.docx` and `.txt` Ingest → Extract →
  Match → Examine → Review → Commit.
- Implemented interface: six FastAPI endpoints and the same six operations as
  MCP tools mounted in the same process, startup demo-project seed, review
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
- A second run reads only what changed and leaves every row it did not affect
  byte-identical, proven on both corpora against the stored rows.
- Each project's folder is watched: poll and quiet period come from
  `config/watcher.yaml`, and nothing starts behind a run that is already in
  flight.
- A document read again that stopped asking for something raises one withdrawal
  proposal for the row it supplied, and only for that row.

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
- [x] `failed`, `ended without changes`, `closed without export` semantics.
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
- [x] Withdrawal end to end — migration `20260814_0007`, the fourth review-queue
      kind, the `Withdrawn` status, the first absence citation, and the export
      that shows it.
- [x] Review fix: the decision stores the document that stopped asking
      (migration `20260814_0008`), so a row cited to two documents has its
      absence written against the one the question named.
- [x] Both corpora driven through a first and a second run inside the suite.

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

| Order | Slice | Scope | Current state |
|---|---|---|---|
| 1 | Reliability proof | Two-project concurrency, same-project queue, injection test | Built on `reliability-proof`; awaiting review and merge |
| 2 | React | One-page five-section review surface | Designed |
| 3 | Operations | Stage timings, token/cost roll-up, measured evidence | Designed |

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
- A row two documents both supplied raises a withdrawal proposal when either of
  them drops it. It is a question the Delivery Owner answers, never a change.
- A document read again whose new extraction comes back a related additional or
  unrelated document withdraws nothing: it never reaches Match, and silence from
  it is silence.
- A withdrawn row is examined like any other, so a rule such as R4 can still
  raise a finding against it.
- A withdrawal is final: a requirement a later document asks for again merges
  its evidence onto the row, and the row still reads `Withdrawn`. Nothing in
  this system updates a committed row's cells from later evidence, so there is
  no gate to carry it back and no honest status to carry it to.
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
- No React or cost/timing reporting yet.
- Neither door authenticates a caller; the MCP endpoint additionally answers
  `421` to a `Host` header other than `localhost` or `127.0.0.1`, so a client
  on another machine cannot reach it as it stands.
- Fresh-clone and image-only verification remain open.

## Next three actions

1. Review and merge the reliability-proof branch.
2. Decide whether the run logger should be given its own stdout handler, so the
   INFO run events D16 describes reach a reader outside a test.
3. Decide whether the already-read rule should settle a related additional
   document the way it settles an unrelated one.

## Verification evidence

| Evidence | Last confirmed | Result / boundary |
|---|---|---|
| `docker compose run --rm app pytest` | 2026-08-14, `reliability-proof` branch | 122 passed, no live key |
| Kill-and-resume | Slice 1 | Real child process + `SIGKILL`; completed extraction not repeated |
| API flow | Slice 1 | One run driven by hand through review/export |
| Northside Dental corpus run | 2026-08-13, `formats-and-types` branch | 6 documents read across `.md`/`.docx`/`.pdf`; unrelated skipped, related additional labelled without a row; 7 rows exported |
| Intake-portal rules run | 2026-08-14, `rules-and-findings` branch | 5 rows examined against R1–R4 plus D1–D2; two R1 findings gated; `finish-review` refused while they were unanswered; one approved and one rejected; export carried the approved finding only, and row 4's fingerprint stayed the seven-cell hash |
| MCP flow | 2026-08-14, `mcp-tools` branch | One run created, started, polled, decided, finished and exported through the six tools; the export refused before approval |
| Intake-portal second run | 2026-08-14, `incremental-update` branch | Meeting notes read first, then the written scope; rows 2 and 3 byte-identical, row 1's cells and fingerprint unmoved while an approved merge added its citations, rows 4 and 6 new |
| Northside Dental second run | 2026-08-14, `incremental-update` branch | Meeting notes read first, then `.docx` scope and `.pdf` testing feedback; the SMS row byte-identical, rows 1 and 3 unmoved through their merges, rows 5 and 7 new |
| Withdrawal on the corpus | 2026-08-14, `incremental-update` branch | The re-issued 26 March scope raised exactly one proposal, on the records-list row it dropped; approving it wrote `Withdrawn`, its cell audit and the absence citation, and the three meeting-note rows were byte-identical |
| Watched folder | 2026-08-14, `incremental-update` branch | An arriving file started a run by itself; a second file arriving during that run's review started nothing until the review finished |
| Two projects at once | 2026-08-14, `reliability-proof` branch | Both runs live together — polled as `running` with a stage set, and two model calls started less than the 2-second call delay apart; rows, citations, decisions, findings and log lines each stayed with the run that produced them |
| Same-project queue | 2026-08-14, `reliability-proof` branch | One waiting run across four requests; its batch held only the file that arrived after it was queued; it started by itself after a `done` run and after a `failed` one |
| Buried instruction | 2026-08-14, `reliability-proof` branch | `meeting-notes-20-mar.md` read in a real run: the line stored and logged as an embedded instruction, one register row from the other document, the export gate the only question asked, and the export refused until it was approved |
| New tests repeated | 2026-08-14, `reliability-proof` branch | Five runs in a row, five passes; no sleep added anywhere |
| Live model | Never | Unverified |
| Fresh clone/image-only | Not run yet | Open release gate |

## Documentation history policy

- Current status is rewritten here; completed dated narrative moves to
  `documentation/progress-history.md`, newest first.
- Never repeat decision rationale here; link to the current decision instead.
- When a blocker resolves, move its resolution and evidence to history and
  remove it from the active list.
- Exact pre-compaction hashes and inventory mapping live in the compaction
  manifest under `documentation/history/`.
