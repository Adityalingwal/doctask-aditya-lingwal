# Live run — the record of every drive

**This file is raw material for the Task 4 write-up, not a permanent part of
the repository.** It holds what the live-model run actually did, drive by
drive, so the write-up can be built from evidence rather than memory. Delete
it once that write-up exists. The lasting summary is in `PROGRESS.md` under
`## Verification evidence`; the decisions the run settled are in
`DECISIONS.md`.

## The three drives of 2026-08-19

Baseline: `main` 7720623, clean tree. Live stack `docker compose -p helplinelive`.
Corpus staged by hand from `sample-documents/helpline-ai/`.

## Trap found first: the running app held pre-fix code

`helplinelive-app-1` started 2026-08-18T21:03:46Z; PR #38's files reached disk at
21:55Z. The bind mount is live but the uvicorn process had already imported the
old modules, so neither the Disputed fix nor the control-character strip was in
effect. The first drive was run against that stale process and returned 6/7.
`docker compose -p helplinelive restart app` before every drive after that.

## Drive A — Luna @ high, single-document staging, MCP (`sample-projects/luna-single-restarted`)

Four runs, one document per batch, chronological. **7/7.**

| Row | Status | Expected |
|---|---|---|
| 1 Voice agent | Done | Done |
| 2 Chat widget | Done | Done |
| 3 WhatsApp | Not delivered | Not delivered |
| 4 Transcripts dashboard | Partial | Partial |
| 5 Weekly report | Handed over | Handed over |
| 6 Hindi/English | Nothing said yet | Nothing said yet |
| 7 Human escalation | **Disputed** | Disputed |

Row 7 is the one that used to land on `Not delivered` across batch boundaries.
Audit trail: `Nothing said yet` → `Handed over` (handover run) → `Disputed`
(testing run), so PR #38's fix is confirmed live.

Rules: the written-requirement rule fired once, on row 7, in the handover run.
The testing-outcome rule fired 14 times across the four runs. The change-request
rule raised no finding — the SMS ask was reported as a dropped observation
("about no requirement the register traces") instead.

Run 2 (the requirements document) raised six possible-match questions; each
pairing was checked against the register before approving, and all six were
correct.

Known limitation seen again, as documented: row 7's `Written down` still reads
"no client requirements document has been read for this project".

## Drive B — Terra @ high, same single staging (`sample-projects/terra-single`)

**7/7** — identical statuses to Drive A.

One difference: Terra never raised the written-requirement finding on row 7
(Luna raised it once). Testing-outcome findings were equal at 14 each. Terra also
produced seven rows from the meeting notes, where the pre-fix corpus had given it
eight — the corpus wording fixes hold.

`config/model.yaml` was switched to `openai/gpt-5.6-terra` for this drive and
restored to `openai/gpt-5.6-luna` afterwards; `git diff` on that file is empty.

## Drive C — Luna @ high, screen, combo 2+2 (`sample-projects/screen-combo`)

Driven entirely through `http://localhost:8000/ui/`: Add-project box, both review
gates, and the register view. Batch 1 = meeting notes + requirements; batch 2 =
handover + testing feedback. **7/7.**

Screen behaviour observed: the creation-time run over the empty folder shows
"no changes"; the Decisions tab previews each cell change before it commits
(row 7 showed `Status: Disputed` before approval); the gate is the two buttons
"Add this run's changes to the register" / "Discard this run's changes", and it
appears only once every decision is answered.

Batch 1 raised no possible-match questions — both documents in one batch, so the
within-batch merge handled it and seven rows came straight out.

Rules: only the testing-outcome rule fired (8 findings). No written-requirement
finding, because by the time Examine ran on batch 2 row 7 already stood at
`Disputed` rather than `Handed over`.

Row 7's `Written down` here reads "Not found in client-requirements-v1.md" —
the documented limitation does not appear when the requirements document is in
the same batch that creates the row.

## What the drives changed in the documentation

`PROGRESS.md` `## Known limitations` said `Disputed` was reached only when the
handover and the contradicting testing feedback were read in one batch. PR #38
changed that and Drive A proved it live, so the entry is gone. Two further
entries there had been left saying "not observed — no live model has run"; both
now say what the run showed. The re-ask noise is real and was measured; the
unchecked evidence copy appeared in its mild form, one shortened sentence out of
three.

## Throwaway state added by this session

Folders: `sample-projects/luna-mcp-single-postfix` (the stale-code drive),
`luna-single-restarted`, `terra-single`, `screen-combo` — four more on top of
the thirteen the earlier drives left, each with a project row in the live
database. The `helplinelive` stack is deliberately still up, because the demo
recording needs a register to show.

Cleared since: three test files that commit `51e5ca8` had deleted were still on
disk untracked and broke `pytest` collection; they are gone, and the suite now
collects its 253 tests with no exclusions.
