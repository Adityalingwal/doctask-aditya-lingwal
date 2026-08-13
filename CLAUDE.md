# Claude Code project instructions

@TASK.md

`TASK.md` is the permanent repository working contract and must be followed in
every session.

## Source priority

1. `documentation/superdocs-engineering-task/SuperDocs-Task-Engineer.pdf` — the
   founder's original brief.
2. `documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`
   — our interpretation of the brief.
3. `DECISIONS.md` — compact current product decisions and status labels.
4. `PROGRESS.md` — current position, open work, assumptions, blockers, and proof.
5. `documentation/decision-history.md` and
   `documentation/progress-history.md` — relevant superseded or completed
   context; do not load them end to end by default.
6. `README.md` — the current user-facing description.

Claude auto-memory is historical context, not project truth. If memory conflicts
with the live repository, follow the source priority above, report the stale
memory, and correct it only after the live files are verified.

## Starting or continuing work

- Before changing anything, inspect Git status plus staged and unstaged diffs.
- Read the current-status section and relevant checklist in `PROGRESS.md`.
- Read the relevant current section in `DECISIONS.md`; open only the matching
  entry in `documentation/decision-history.md` when history affects the work.
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
- When a decision changes, append the old wording, rationale, and supersession
  link to `documentation/decision-history.md`, then update root
  `DECISIONS.md` to current truth.
- After work completes, update root `PROGRESS.md` and move completed dated
  narrative to `documentation/progress-history.md`; do not turn either file
  into a second decision log.
- If a genuinely reusable repository working rule is discovered, discuss it
  with Aditya first. Once agreed, add or update it in `TASK.md`; do not promote a
  one-off correction or preference into a permanent rule.
- Update `README.md` only when current user-facing behaviour, setup, commands,
  formats, domain, or limitations change.
- After live files are correct, update stale Claude auto-memory so it points
  back to the repository instead of duplicating the full specification.
- Before finishing documentation work, search for stale terminology and
  conflicting locks, then run `git diff --check`.
