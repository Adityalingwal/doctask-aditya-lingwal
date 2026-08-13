# PROGRESS.md — current project dashboard

Current status only. Detailed dated narrative is archived in
[`documentation/progress-history.md`](documentation/progress-history.md); the
exact pre-compaction source is
[`documentation/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md`](documentation/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md).
Decision rationale belongs in `DECISIONS.md`, not here.

## Snapshot — 2026-08-13

- Slice 1 (1a + 1b + eight review fixes) is merged into `main`.
- 51 tests pass without a live API key.
- No live model call has been made; all runs/tests used the scripted client.
- Implemented pipeline: `.md` Ingest → Extract → Match → Review → Commit.
- Implemented interface: six FastAPI endpoints, startup demo-project seed,
  review queue, JSON/Markdown export.
- Verified reliability: real-process `SIGKILL` resume, no repeated completed
  extraction, Ingest/Match re-entry safety, honest terminal statuses.
- Durable per-project lock and one waiting-run queue are built; dedicated
  concurrency proof is pending.
- Demo corpus has one actual document. Three remaining intake-portal documents
  and six Northside Dental documents are designed but not written.

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

## In progress / next slices

| Order | Slice | Scope | Current state |
|---|---|---|---|
| 1 | Formats and types | PDF/DOCX/TXT readers, page limit, bucket enforcement, second corpus files | Next |
| 2 | Rules and findings | Examine, findings table, config snapshot/fingerprint, R1–R4/D1–D2 | Waiting on audit-schema blocker |
| 3 | MCP | Six thin in-process tools over shared core functions | Designed |
| 4 | Incremental proof | Watched folder, focused proposals, byte-identical unchanged-row proof | Designed |
| 5 | Reliability proof | Two-project concurrency, same-project queue, injection test, review replay guard | Partly built |
| 6 | React | One-page five-section review surface | Designed |
| 7 | Operations | Stage timings, token/cost roll-up, measured evidence | Designed |

Later-slice absence is not a defect in Slice 1. Each capability becomes a
working claim only after its own implementation and proof land.

## Active blockers

1. **Audit cannot store attachment events.** `audit.cell_name` is `NOT NULL`
   and constrained to seven register cells, while the contract requires events
   such as a finding attached to a row. Resolve in the rules/findings slice
   before attachments are written.
2. **Document-type buckets are not enforced.** Extract accepts expected values,
   but only `unrelated` changes control flow; an unexpected type is treated as
   related. Resolve in the formats/types slice.
3. **Development Compose mount is too broad for final proof.** `.:/workspace`
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
| Lock/queue isolate concurrent work | Schema + indirect resume exercise | Dedicated two-project and same-project tests |
| Default OpenRouter model is suitable | Configured but never called | Bounded live-model run |

## Known limitations

- Only `.md` is implemented although four formats are declared.
- One Extract call may repeat in the answer-to-checkpoint kill window.
- A rejected finding stays suppressed if later evidence strengthens it.
- Files arriving during Review wait; that run holds the project lock.
- No watcher, rules/findings, MCP, React, cost/timing, or unchanged-row proof yet.
- `review_finished_at` replay protection and loopback-only bind are locked but
  not implemented.
- Fresh-clone and image-only verification remain open.

## Next three actions

1. Finish this documentation compaction and independent review; merge only
   after zero-loss and consistency checks pass.
2. Build the formats/type slice, including bucket enforcement and the remaining
   synthetic corpus files needed for its tests.
3. Start rules/findings only after its brief explicitly includes the audit
   attachment-schema blocker.

## Verification evidence

| Evidence | Last confirmed | Result / boundary |
|---|---|---|
| `docker compose run --rm app pytest` | 2026-08-13 pre-compaction baseline | 51 passed, no live key |
| Kill-and-resume | Slice 1 | Real child process + `SIGKILL`; completed extraction not repeated |
| API flow | Slice 1 | One run driven by hand through review/export |
| Live model | Never | Unverified |
| Concurrency suite | Not run/built yet | Mechanism exists; proof pending |
| Fresh clone/image-only | Not run yet | Open release gate |

## Documentation history policy

- Current status is rewritten here; completed dated narrative moves to
  `documentation/progress-history.md`, newest first.
- Never repeat decision rationale here; link to the current decision instead.
- When a blocker resolves, move its resolution and evidence to history and
  remove it from the active list.
- Exact pre-compaction hashes and inventory mapping live in the compaction
  manifest under `documentation/history/`.
