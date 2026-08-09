# PROGRESS.md

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-09.** Task 1 scoping is complete — every decision and its reasoning
is in `DECISIONS.md`. Nothing about the system's design is restated here.

`TASK.md` is written apart from its Commands section, which stays empty until
the project structure exists.

No code yet. Next: a throwaway LangGraph exercise — five nodes, a checkpointer,
an `interrupt()`, then kill the process and resume it — to get the runtime's
concepts in hand before designing the real graph.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in request matching; the whole register fits in one model call, so nothing needs narrowing | Open — breaks if a real pile produces hundreds of rows |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, request lists and testing feedback are short by nature, so vector retrieval may not be needed at all | Open — if real documents turn out large, pgvector retrieval comes back in |

## Blockers

_None open._

## Log

Newest first.

**2026-08-09 — Task 1 scoping complete, `TASK.md` written**
Worked through the orchestration choice and the full domain scoping in one
pass. Rejected alternatives are recorded in `DECISIONS.md` so they do not
resurface. Wrote `TASK.md`: what this is, where the truth lives, code
conventions, a never-do list split into "the system must never" and "you must
never", a definition of done, and the git rule (branch commits and pull requests
allowed, merging is not).
