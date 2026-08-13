# Documentation compaction manifest — 2026-08-13

## Result

The active documentation was compacted without deleting recoverable project
information. Root files now carry current truth; detailed chronology is in the
two history files; exact byte-for-byte pre-compaction sources are preserved as
snapshots. A mechanical TSV inventory maps every counted source item.

No product decision or implementation changed in this work.

## Git boundary

- Baseline branch: `main`
- Baseline commit: `2e14c9177cc0c9e782b2bd7d791cb653bd157ee5`
- Work branch: `codex/docs-compaction`
- Active-doc final content commit: `2200d39`
- Earlier compaction commits: `4558236` (archives), `fa37e55` (current
  decisions/progress), `2200d39` (README and routing)
- State at verification: clean tracked tree at `2200d39`, with only this
  manifest and its TSV inventory pending for the final audit commit.
- PDF rule followed: `SuperDocs-Task-Engineer.pdf` was not opened or read.

## Files and hashes

### Exact pre-compaction snapshots

| File | Lines | Bytes | SHA-256 |
|---|---:|---:|---|
| `documentation/history/DECISIONS-pre-compaction-2026-08-13-2e14c91.md` | 3,063 | 221,505 | `cb54be6538d36178d1d6e71501362590005377d7859938e692a3fdc0646d13a7` |
| `documentation/history/PROGRESS-pre-compaction-2026-08-13-2e14c91.md` | 316 | 19,720 | `5f752a2e8c75b4b9d8e4fd7cdf0aeed7135313ab8055b5712b38d60c9d129aca` |

The hashes equal the original root-file hashes recorded before editing.

### Current active documents

| File | Baseline lines/bytes | Final lines/bytes | Final SHA-256 |
|---|---:|---:|---|
| `DECISIONS.md` | 3,063 / 221,505 | 572 / 30,363 | `f1e8a8c357210c4e0abb6ec87508762f334aab7d476ba346d3344273ceebce16` |
| `PROGRESS.md` | 316 / 19,720 | 127 / 6,851 | `999baaf5f896488dc556b7b35a60afd74871dea260e1a3bb3a249bca305f9091` |
| `README.md` | 96 / 4,107 | 130 / 5,159 | `16cc9146f7cfde9c6b015a3c3aa46a8bae937ef3f566fa7ed7367774528becbe` |
| `TASK.md` | 255 / 12,179 | 256 / 12,477 | `d2ad85caeacb7f3e773fc1508ea1e8ce696eb8bb4b38430f08e52d4ef081f45a` |
| `CLAUDE.md` | 58 / 2,896 | 64 / 3,193 | `5a10ac82e2d5811b62fc8002dd477f48b0faba39e7064912da2dcbdb22f25129` |

The three default active files (`DECISIONS.md`, `PROGRESS.md`, `README.md`)
fell from 245,332 to 42,373 bytes: **82.73% reduction**.

Soft size guidance was not treated as a destructive target. `DECISIONS.md` is
78 lines below its suggested range because the D01–D17 index carries the same
current contracts more densely. `README.md` is 10 lines above its suggested
range to retain honest setup boundaries and limitations. `PROGRESS.md` is
inside its range.

### History and inventory

| File | Lines | Bytes | SHA-256 |
|---|---:|---:|---|
| `documentation/decision-history.md` | 3,075 | 221,975 | `8727f4d59ace7e8bd53aec4d6ca4c6d7789dcd4dc7138f448886c9a5dc0b36e0` |
| `documentation/progress-history.md` | 328 | 20,200 | `d908cc70a5651fdc4aa76010f8178181af1f59fcc3fbf3c4d98cb7ab0d8a1801` |
| `documentation/history/documentation-compaction-inventory-2026-08-13.tsv` | 166 | 32,578 | `89e7def8be790f68c33e282cff0a4c0ccd693454bc6a6d44a8b49eb3c13473fc` |

## Loss inventory

Inventory source counts and destinations:

| Source item | Count | Current/history destination | Missing |
|---|---:|---|---:|
| Decision Log rows | 93 | Root D01–D17/superseded index + verbatim decision history + exact snapshot | 0 |
| Decision canonical H2 sections | 42 | Root current families + detailed decision history + exact snapshot | 0 |
| Progress H2 sections | 5 | Root dashboard + progress history + exact snapshot | 0 |
| Progress assumptions | 6 | Root active assumptions + progress history + exact snapshot | 0 |
| Progress blockers | 3 | Root active blockers + progress history + exact snapshot | 0 |
| Progress dated Log entries | 16 | Progress history + exact snapshot | 0 |

The older `rg '^**2026-'` count was 17 because it also counted the dated
current-status paragraph at source line 10. That paragraph is covered by the
`Where things stand` section mapping; the actual `## Log` contains 16 entries.

### Canonical-section map

| Pre-compaction H2 | Current destination |
|---|---|
| Decision Log | Current decision index + Superseded index; verbatim in decision history |
| Vocabulary | `DECISIONS.md` Vocabulary |
| PDF library choice | D04 Formats and document types |
| Orchestration framework decision | D12 State/checkpoints + D17 proof |
| Deliverable shape | D01 Product contract |
| Domain | D01 Product contract |
| Target user and human reviewer | D01 Product contract |
| Human-gate scope | D02 Human review |
| Human-gate actions | D02 Human review |
| One-run scope | D01 Product contract |
| Incremental input contract | D03 Input and incremental updates |
| Declared set — formats and types | D04 Input and incremental updates |
| Document types | D04 Input and incremental updates |
| Register shape | D05 Register and evidence |
| Citations | D05 Register and evidence |
| Export, audit history, unchanged proof | D05/D06 Register and evidence |
| Pipeline stages | D07 Pipeline |
| Extract | D08 Extract |
| Prompt-injection resistance | D08 Extract |
| Match and Examine | D09 Match + D10 Examine/findings |
| Model provider and client | D11 Model boundary |
| Failure and retry behaviour | D11 Failure contract |
| Logging, timing, and cost | D16 Operations |
| Run state and checkpoints | D12 Reliability |
| Run identity and concurrency | D13 Reliability/concurrency |
| Review re-entry after finished review | D02 Human review + D12 Reliability |
| Extract-call idempotency | D08 Extract + D12 Reliability |
| Database tables — slice 1 | D14 Storage and interfaces |
| API — slice 1 | D14 Storage and interfaces |
| MCP server — tool surface | D15 Storage and interfaces |
| MCP server — placement and validation | D15 Storage and interfaces |
| Requirement identity | D09 Match |
| Requirement granularity | D09 Match |
| Rules and playbook | D10 Examine and findings |
| Findings storage and run configuration | D10 Examine and findings |
| Repository layout | D17 Delivery plan |
| Review interface — scope | D15 MCP and React |
| Build order — vertical slices | D17 Delivery plan |
| Brief acceptance contract | D17 Acceptance summary |
| Slice 1 automated test strategy | D17 Test contract |
| One-command setup and test plan | D17 Setup contract + README |
| Network bind | D17 Network bind + README limitation |

### Progress-section map

| Pre-compaction section | Current destination |
|---|---|
| Where things stand | `PROGRESS.md` Snapshot |
| Planning roadmap | Completed + In progress/next slices + Next three actions |
| Assumptions | Active assumptions table; original rows retained in history |
| Blockers | Active blockers; original prose retained in history |
| Log | `documentation/progress-history.md` |

## Working-notes coverage

The working notes remain the complete interpreted brief; they were not
compressed or duplicated. Current Task-1 routing was checked as follows:

| Working-notes requirement family | Current destination |
|---|---|
| Stack and orchestration | D11–D15, D17 |
| Domain/source-data boundary | D01, README Domain |
| Grounded multi-document outcome | D01, D05, D10 |
| Visible agentic stages and branching | D07, D17 behaviour #1 |
| Stop/resume | D12, D17 behaviour #2 |
| Human gate | D02, D17 behaviour #3 |
| Machine interface | D14/D15, D17 behaviour #4 |
| Fresh-clone reproducibility | README Run/Test, D17 behaviour #6 |
| Key-free automated tests | D17 behaviour #7, PROGRESS verification |
| Prompt-injection resistance | D08, D17 behaviour #8 |
| Concurrent-run safety | D13, D17 behaviour #9 |
| Cost/timing visibility | D16, D17 behaviour #10 |
| No-bluff reliability | D05, D09, D11 |
| User-supplied rules | D10 |
| Incremental updates/audit/unchanged proof | D03, D05/D06 |
| Repository/submission honesty | README, TASK, PROGRESS |
| Working method and fresh verification | TASK, PROGRESS, this manifest |

Task 2–4 requirements remain in the working notes rather than being copied
into Task 1 current-product files. No later-slice absence was relabelled as a
Slice-1 defect.

## Consistency and verification

Commands and outcomes:

| Check | Result |
|---|---|
| Full required files read | `TASK`, `CLAUDE`, current `DECISIONS`, current `PROGRESS`, `README`, working notes, config README, sample-projects README read in full |
| PDF exclusion | Not read |
| Live code/status inspection | Routes, graph, statuses, migrations, configs, Dockerfile/Compose, tests and recent Git history checked |
| Exact snapshot hashes | Both match their source baseline hashes |
| Inventory count | 165 mapped items + one TSV header; zero missing |
| Active stale-claim scan | No matches for the selected stale system/endpoint/status/history phrases |
| Local history links | All six referenced local targets exist |
| `git diff --check 2e14c91..2200d39` | Pass |
| `git diff --check` for pending audit artifacts | Pass |
| Full tests | `python -m pytest` in the existing configured Docker app environment: **51 passed in 41.94s** |

Test-environment diagnostics before the successful run:

1. A new Compose project could not publish PostgreSQL because host port 5432
   was already occupied by the existing healthy project.
2. The existing container's old `/workspace` bind target was empty, so direct
   `pytest` collected zero tests.
3. The current worktree was copied to a container `/tmp` path and run with
   `python -m pytest`, reusing its configured PostgreSQL environment without
   reading or exposing credentials. That run collected all 51 tests and passed.

## Trust boundaries and remaining ambiguity

- This is a documentation-only change; tests prove no code regression but do
  not convert later-slice designs into working features.
- No live model run, fresh clone, image-only run, dedicated concurrency suite,
  or second-corpus run was performed. Root docs state each boundary.
- The full historical files are intentionally large and are not default read
  targets. Root routing instructs future agents to open only relevant history.
- Exact snapshots intentionally duplicate historical content. They are audit
  artifacts, not competing canonical sources.
- No information was judged safe to delete permanently; compact root prose is
  recoverable through history, snapshot, and inventory mapping.
