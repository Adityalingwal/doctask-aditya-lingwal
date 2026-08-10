# PROGRESS.md

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-11.** Task 1 scoping is active again. The domain contract is now
**Software Requirements-to-Delivery**, with Client and Software Provider as the
actors; the workflow boundary, primary document types, and core domain cases are
locked in `DECISIONS.md`.

The previous register choice is reopened. Next decision: register vs brief vs
report. Architecture work starts only after the remaining product decisions are
closed.

The pending consistency audit covers the review-screen scope, configurable vs
hardcoded formats, the separate classify stage, citation-preserving extraction,
run idempotency, and the unverified small-register/short-document assumptions.

`TASK.md` is written apart from its Commands section, which stays empty until
the project structure exists.

**LangGraph learning exercise complete.** A throwaway five-node graph with
SQLite checkpointer, interrupt/Command, and kill-and-resume was built and tested
externally. The six core concepts (State, Node, Edge, Conditional Edge,
Checkpointer, interrupt/Command) are in hand.

**Ingest pipeline scoping started.** PDF library choice locked: `pdfplumber` for
extraction, `pypdf` for encryption detection. Decision and evidence in
`DECISIONS.md`. Accepted formats declared in `README.md`.

No code yet in this repository.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in request matching; the whole register fits in one model call, so nothing needs narrowing | Reopened 2026-08-11 — depends on choosing a register and measuring real sample piles |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, client requirements documents, and testing feedback are expected to be short, so vector retrieval may not be needed | Open — if real documents turn out large, pgvector retrieval comes back in |

## Blockers

_None open._

## Log

Newest first.

**2026-08-11 — Domain corrected; deliverable reopened**
Replaced the previous software-feature-delivery framing with the agreed
Software Requirements-to-Delivery contract across `README.md`, `TASK.md`, and
`DECISIONS.md`. Reopened register vs brief vs report; queued six consistency
issues for their relevant decision blocks before architecture begins.

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
