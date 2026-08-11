# Claude Code project instructions

@TASK.md

`TASK.md` is the permanent repository working contract and must be followed in
every session.

## Source priority

1. `documentation/superdocs-engineering-task/SuperDocs-Task-Engineer.pdf` — the
   founder's original brief.
2. `documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`
   — our interpretation of the brief.
3. `DECISIONS.md` — current product decisions and superseded decision history.
4. `PROGRESS.md` — current position, open work, assumptions, and blockers.
5. `README.md` — the current user-facing description.

Claude auto-memory is historical context, not project truth. If memory conflicts
with the live repository, follow the source priority above, report the stale
memory, and correct it only after the live files are verified.

## Starting or continuing work

- Before changing anything, inspect Git status plus staged and unstaged diffs.
- Read the current-status section and relevant checklist in `PROGRESS.md`.
- Read the relevant current section and related history in `DECISIONS.md`.
- Continue from the relevant open item; do not silently reopen or reinterpret a
  locked decision.
- If the brief, current decisions, and requested work disagree, stop and ask
  Aditya before editing or implementing.

## Working with Aditya

- Use concise, beginner-friendly Hinglish unless he asks otherwise.
- Discuss one small decision at a time; avoid multi-topic design dumps.
- Do not convert a discussion into file edits until Aditya explicitly locks the
  decision or asks for the edit.
- Do not start implementation while required product-contract decisions remain
  open unless Aditya explicitly requests a narrow exploratory spike.
- Do not make a product assumption merely to keep moving; ask when the answer
  would materially change behaviour or architecture.

## Keeping project knowledge current

- Follow the documentation-maintenance rules imported from `TASK.md`.
- When a decision changes, preserve the old Decision Log row as `SUPERSEDED`,
  add the replacement row, and update the canonical section to current truth.
- After a decision is locked or work completes, update `PROGRESS.md` current
  status, checklist, and dated log without turning it into a second decision log.
- If a genuinely reusable repository working rule is discovered, discuss it
  with Aditya first. Once agreed, add or update it in `TASK.md`; do not promote a
  one-off correction or preference into a permanent rule.
- Update `README.md` only when current user-facing behaviour, setup, commands,
  formats, domain, or limitations change.
- After live files are correct, update stale Claude auto-memory so it points
  back to the repository instead of duplicating the full specification.
- Before finishing documentation work, search for stale terminology and
  conflicting locks, then run `git diff --check`.
