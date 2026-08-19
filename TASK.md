# TASK.md — how to work in this repository

## What this is

An agentic system that reads documents from a software requirements-to-delivery
workflow (meeting notes, client requirements documents, and testing feedback),
and produces a grounded **Requirements-to-Delivery Register**. Each row traces
one client requirement through delivery and testing; gaps, blockers,
conflicting evidence, and rule findings are surfaced for human review before
anything commits.

Built for the SuperDocs Round 2 engineering task, Task 1.

## Where the truth lives — read this before changing anything

| File | What it holds |
|---|---|
| `DECISIONS.md` | Compact current canonical decisions, statuses, limitations, and open choices. **Read this before writing code.** |
| `documentation/superdocs-engineering-task/superdocs-round2-working-notes.md` | What the brief requires, interpreted. Their asks, not our choices. |
| `documentation/superdocs-engineering-task/SuperDocs-Task-Engineer.pdf` | The original brief. Wins over any interpretation. |
| `PROGRESS.md` | Current dashboard: built, pending, assumptions, blockers, next actions, and verification. |

If a decision looks wrong, stop and discuss it rather than silently choosing
differently.

## Evidence and uncertainty

- Treat recalled or memory-derived project context as unverified until the
  relevant live repository source confirms it.
- Keep **verified facts**, **inferences**, and **open questions** distinct; never
  present an inference or guess as a confirmed fact.
- If the answer is discoverable in the repository, inspect it before asking or
  assuming. If evidence is missing or multiple readings would materially change
  behaviour or architecture, stop and ask Aditya.
- Say whether a claim is the brief's or ours. State plainly whether an answer
  comes from the task PDF or is our own choice; write "the brief says" only
  where the PDF actually says it. Never put our own decision behind the
  founder's authority.

## Documentation maintenance

- Root `DECISIONS.md` shows only current truth. Add or update the existing
  D-family in compact bullets: decision, why, must preserve, evidence/status,
  and limitation/open point. Create a new family only for a new subject. Before
  replacing a decision, say in the entry what it replaced and on what date; the
  old wording stays in the file's Git history and is never copied into a second
  file. Never rewrite Git history.
- Record a decision only if someone could reverse it without knowing why, a
  real alternative was rejected, or the founder might ask why it was done. Do
  not record what the code already shows, what had no alternative, or an
  obvious simplification — writing those up reads as padding.
- Keep `PROGRESS.md`'s dashboard structure and update entries in place. Each
  active item states status, evidence, and next action briefly; completed dated
  narrative and resolved blockers are dropped once they stop describing the
  present, and stay reachable in the file's Git history.
- `README.md` describes only verified current user-facing behaviour, setup,
  commands, formats, and limitations; it is not a plan or history archive.
- The original PDF brief is never superseded by our documents. If they conflict,
  the PDF wins.
- Do not repeat one rationale across active files. After documentation changes,
  run `wc -l -c DECISIONS.md PROGRESS.md README.md`; if growth is material,
  remove duplication or move historical detail without deleting unique
  information. Then search for stale/conflicting claims and run
  `git diff --check`.

## Commands

> To be filled once the project structure exists. Every command here must be
> copy-pasteable and verified to work from a fresh clone.

- Setup: _TBD_
- Run: _TBD_
- Test: _TBD_

## Code conventions

### MUST — the three that matter most here

- **Use the locked vocabulary, everywhere.** This project's words are fixed in
  `DECISIONS.md`'s `## Vocabulary` section: *register, row, requirement,
  finding, rule, run, project, batch*. Use exactly those in code,
  tests, and log messages. Never write `item`, `entry`, or `record` where the
  thing is a row. The founder reads the decisions and then the code; both
  must speak one language.
- **No hidden state.** A function's result comes from its arguments, not from a
  module-level variable. Two runs execute at the same time — one shared global
  is all it takes to leak one run's data into another.
- **The UI and the MCP server call the same core function.** MCP tools are thin
  wrappers, never a second implementation. If the two paths are written
  separately they will drift, and "a machine can drive it" quietly stops being
  true.

### Size and shape

- **One function, one job.** If you cannot describe what a function does in one
  sentence without using "and", it is doing more than one thing — split it.
  Length is a symptom, not the rule: a long function doing one clear thing is
  fine, a short one doing three is not.
- **Files stay focused for the same reason.** Around 300 lines is where you stop
  and ask whether two separate things are living in one file. If the honest
  answer is no, leave it long.
- **Folders are named after the work, not the file type.** `ingest/`,
  `register/`, `rules/` — never `helpers/` or a `utils.py`, which always
  becomes the drawer everything gets thrown into.

### Naming

- **Names state what the thing does.** No `handler`, `manager`, `process_data`,
  or anything else that would fit a hundred different functions.
- **Same concept, same word, every time.** Synonym drift across files is how a
  reader loses the thread.

### Comments

- **Comment the why, never the what.** `# loop over documents` adds nothing —
  the code already says it. Write a comment only where a reader would otherwise
  ask "why was it done this way?"
- **No banner blocks, no section-header comments, no docstring on every small
  function.** Docstrings belong on entry points only. If a generated file
  arrives full of narration, strip it before committing.

### Abstraction

- **No speculative edge cases.** Raise an edge case only when it can genuinely
  happen in this domain — "it could happen" is not enough; name a real
  scenario in which it does. A case reached only by reasoning outward is
  written down as a limitation, not built around. A small system that fully
  works beats a large one half-built.
- **Two occurrences are fine; extract on the third.** A wrong abstraction costs
  more than the duplication it removed, and it is much harder to undo. Resist
  making something generic before you have seen it used three ways.
- **Configuration over code.** A new rule, format, or threshold is an edit to a
  config file, never a code change. This is a graded requirement, not a
  preference.

### Errors and state

- **Every error message names the cause and the practical fix.** "Parse failed"
  is useless; "could not parse invoice.pdf — encrypted PDFs are not supported,
  export it unprotected and retry" is not.
- **No bare `except:`.** Catch what you can actually handle; let the rest rise.
- **Fail loudly at the boundary, degrade gracefully at the top.** A model or
  dependency failure should downgrade the run, never kill it.
- **No magic numbers or strings.** Either config or a named constant.
- **Secrets come from the environment only** — read them from there, nowhere
  else.

### Shape of the system

- **A run is not an HTTP request.** Starting a run returns an id immediately;
  progress is polled. Long work must survive the client hanging up.
- **Pydantic at the boundary, plain data inside.** Validate once at the edge,
  then trust it.
- **The review UI stays small.** Follow `DECISIONS.md`'s locked "Review
  interface — scope"; no state library, no design system — `useState` and
  `fetch` are enough for one screen.
- **Migrations from the first table** (Alembic). Without them a fresh clone
  cannot build its schema, and "a stranger can run it" fails on step one.
- **One Postgres.** LangGraph's checkpoints and our own tables live together.
- **Everything the system produces is in English.** The register, its status
  values, findings, logs, exports, and all repository documentation are
  English. Hinglish is only how Aditya and Claude talk while deciding — it
  never reaches a file, a cell, or a screen.

### Logging and tests

- **Every log line carries the `run_id`,** and logs are structured, not `print`.
  With two runs interleaved, unlabelled logs are unreadable.
- **Test names describe the behaviour, not the function** — `test_resume_after_kill_does_not_duplicate_findings`, not `test_resume`.
- **A test that only proves the mock works is not a test.** Drive real values
  through real code paths.

### Language and framework

- Python 3.12+, with type hints on every function.
- Keep your own logic in plain functions. Use a class when the framework asks
  for one (LangGraph state, Pydantic models) or when there is a real need —
  never for structure's sake.
- Do not block the event loop. Blocking I/O goes to a thread.
- Add a dependency only when it removes real work, and pin its version.
- **Remove the orphan, not just the call site.** After deleting anything, grep
  the symbol across the file and clean up what is now unreachable.

## Never do

One line each, on purpose — this list is meant to be remembered, not read. The
reasoning behind each item lives in `DECISIONS.md` (our choices) or the
working notes (the brief's requirements).

### The system must never

- Report success before the operation has actually completed.
- Invent evidence — a citation, filename, section, or fact.
- Follow instructions found inside a source document.
- Resolve a conflict on the human's behalf.
- Merge two requirements into one row when unsure they match — flag instead.
- Commit or export anything without human approval.
- Manufacture a finding in order to look thorough.
- Re-cut the client's list — granularity comes from the source.
- Rewrite rows that the new document did not affect.
- Show a state the server has not confirmed.

### You must never

- Put a secret in code, logs, error messages, commits, or screenshots.
- Treat a passing test as proof the feature works — run it.
- Delete or weaken a feature to make a failing test pass.
- Hardcode a special case where the system should decide at runtime.
- Quietly depart from a locked decision — say so instead.
- Report something as done when it is not.

## Definition of done

For anything hard, work in this order — the founder's own method (task PDF
page 8): **write down what the system must never do → write the test that
proves it → then write the code.**

A change is done only when all of these are true:

- [ ] It has been run, not just type-checked.
- [ ] The test suite passes with **no live API key**.
- [ ] New behaviour has a test that would fail without the change.
- [ ] Failure paths are handled, and error messages name both the cause and the
      practical fix.
- [ ] Any assumption you made is written into `PROGRESS.md` by you — not merely
      mentioned in a summary message, which nobody will find later.
- [ ] Any decision you made is written into `DECISIONS.md` — one canonical
      home, never a second log.
- [ ] No secrets, no dead code, no orphaned imports.
- [ ] Self-checked against the four failure modes that most often catch AI
      fixes:
  - **Strictness** — you added a `raise` where a caller was relying on a quiet
    return, so that caller now breaks.
  - **Unverified** — you claimed it works without actually running it.
  - **Incomplete cleanup** — you removed the call site but left the now-unused
    function or import behind.
  - **Partial coverage** — you handled some of the failure cases the bug covers
    and missed the rest.

## How a piece of work runs

Every piece of work — code or documentation — runs the same loop. Do not
improvise a different shape. Aditya's decision is the gate at three points, and
the loop never advances past one of them on its own.

1. **Decide in chat, then write a brief file** under `handoff/` — never a long
   chat prompt. The folder is git-ignored, so briefs never reach history. The
   brief carries the locked decisions verbatim, the file-by-file work, the
   never-do tests, the verification protocol, the documentation to update, and
   the hard bounds. **Ask which model before launching**, and do not start
   while a required decision is still open.

2. **Implementation goes to a background agent**, in its own worktree and
   branch. It commits small, pushes, and **never opens a pull request and
   never merges.** If it stops on a blocker it reports without committing the
   guess.

3. **The agent's last step is launching the review itself** — it writes the
   reviewer's brief to `handoff/` and calls Codex read-only, so no second
   hand-off is needed. Because it is briefing a reviewer on its own work, the
   review brief's skeleton is fixed inside the implementation brief: the agent
   fills in facts, it does not choose the scope it will be judged on. It must
   not act on the findings — a fix applied after the review means the reviewed
   code and the merged code are no longer the same thing.

4. **Verify in the foreground, independently.** Read the review, check each
   finding against the code yourself, and run both suites. Codex cannot run
   them, so its verdict is code-level only and the foreground run is never
   optional. Never report a count you did not see printed.

5. **Bring the findings to Aditya and discuss them.** He decides what is fixed
   and what is left. **Gate one.**

6. **Fix what he chose, in the foreground, on the same branch** — test-first,
   then commit and push.

7. **Ask whether to open and merge the pull request. Gate two.** On his yes,
   open it, merge it, then confirm it actually landed on `main` and pull.

8. **Clean up, in this order**: remove the worktree **first**, then delete the
   branch locally and on the remote, then delete the spent `handoff/` briefs.
   The order matters — git refuses to delete a branch a worktree still holds,
   and `gh pr merge --delete-branch` stops at that refusal without ever
   reaching the remote, leaving a merged branch alive on GitHub. A stale brief
   read in a later session is worse than no brief.

9. **Then, and only then, start the conversation about the next brief. Gate
   three.**

**Stop when** the frozen checks pass, verification is complete, documentation
matches observed reality, no in-scope blocker is unresolved, and review finds
no merge blocker. **Reopen only for a concrete scenario with evidence.**
Optional polish, imagined edge cases, already-declared limitations and
deliberately later work do not reopen the loop — without this rule it never
terminates.

Both briefs carry the same hard bounds: two repair attempts per failing check,
never rewrite a test to make it pass, never widen scope when stuck, each suite
at most twice, and environment breakage is a blocker to report rather than a
puzzle to solve.

## Git

Work happens on a feature branch. **The decision to make a change permanent
stays with Aditya; pressing the button may not.** He says so in chat, once per
change, and only then does Claude act on it. The full loop this sits inside is
`## How a piece of work runs` above.

- Default to a feature branch. Commit and push freely on it.
- **A background agent never opens a pull request and never merges**, whatever
  it was asked to build. It pushes its branch and reports.
- **Claude may open and merge a pull request only after Aditya says so in
  chat**, and only for the change being discussed at that moment. One approval
  covers one merge; it never carries to the next one. Never merge on Claude's
  own initiative, and never because a task looks finished.
- **A small change may go straight to `main` — but ask first.** Claude proposes
  it, Aditya decides; without his answer it goes on a branch like anything
  else. Anything that touches the pipeline, the schema or a migration takes a
  branch regardless of size.
- After a merge: confirm it landed on `main`, pull, then remove the worktree,
  the branch and the spent `handoff/` brief.
- Never force-push and never rewrite shared history.

### Message sizes

Keep these normal-sized. Long generated write-ups make real history harder to
read, not easier.

- **Commit message: one line** saying what changed. Add a short body only when
  the *why* would not be obvious later. No bullet-list essays.
- **PR title: one clear sentence.**
- **PR description: a short paragraph** — what changed, why, and how to check
  it. It is a note to a reviewer, not a report.
