# PROGRESS.md

Running log of what is built, what was assumed, and what is blocked.
Locked decisions and their reasoning live in `DECISIONS.md`, not here.

## Where things stand

_Rewritten in place — this section always describes the present, not the past._

**2026-08-11.** Phase 1 (product contract) and Phase 2 (information design)
are both complete — see the Planning roadmap below. The domain contract is
**Software Requirements-to-Delivery**, with Client and Software Provider as
the actors; the workflow boundary, primary document types, and core domain
cases are locked in `DECISIONS.md`.

The final deliverable is the **Requirements-to-Delivery Register** — seven
columns, per-cell citations, five status values. The provider-side Delivery
Owner is both the system user and human reviewer. One run is one complete
processing cycle for one submitted document batch; the incremental input
contract now defines what a batch is and who starts a run. The human-gate
scope and its two actions, Approve/Reject, are locked in `DECISIONS.md`.

Phase 3 (system architecture) is under way and deliberately partial: the
architecture slice 1 needs is now settled — pipeline stages and LangGraph
state/checkpoints in full, plus the slice-1 share of run identity (a
random-UUID run id, one run per project by database lock, a queued second
run), database tables (seven), and the API (five endpoints) — so
implementation can begin. The rest of Phase 3 is decided alongside the
slice that needs it.

The pending consistency audit covers the review-screen redesign, run
idempotency, and the still-open short-document/pgvector assumption. The
review screen's `DECISIONS.md` mockup is no longer a silent contradiction —
it now carries a banner naming the three things about it that are outdated;
the redesign itself stays deferred to the architecture phase (see "Review
interface — scope" in `DECISIONS.md`).

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

Documentation history now follows an explicit policy: the Decision Log is
append-only, canonical sections contain only current truth, and current-facing
files do not carry stale alternatives. Root `CLAUDE.md` imports the repository
working contract and defines source priority and continuation rules for future
Claude Code sessions.

## Planning roadmap

This section tracks only status and continuation order. Decision reasoning stays
in `DECISIONS.md`; implementation detail belongs in code and tests.

**These four are not four gates in a row.** Phases 1 and 2 are closed, but
phase 3 is not finished before code starts. Only what the first slice needs is
settled first — components and data flow, and LangGraph state and checkpoints,
in full; plus the slice's share of run identity, database tables and
migrations, and the API. The rest — parsing and model boundary, the
human-review state machine, watched folder and focused update, prompt-injection
and no-bluff controls, failure and cost behaviour — is decided alongside the
slice that needs it. Phase 4's items are per-slice too, not a gate before
implementation. This follows the locked build order: checkpoint granularity
cannot be designed honestly without watching a real checkpointer behave, and
every graded behaviour is a runtime property no dummy-data scaffold can
exercise.

### 1. Product contract

- [ ] Define the brief acceptance contract with exact pass/fail checks.
      Deferred to build time — decision recorded in `DECISIONS.md`.
- [x] Lock domain, actors, workflow boundary, and document types.
- [x] Select the Requirements-to-Delivery Register.
- [x] Choose the actual system user and human reviewer.
- [x] Define one-run scope.
- [x] Define the human-gate scope.
- [x] Define the incremental input contract.
- [ ] Decide coverage or defended cuts for behaviours 6–10. Deferred to build
      time — decision recorded in `DECISIONS.md`.
- [ ] Lock the React, FastAPI, and MCP boundary. Deferred to build time —
      decision recorded in `DECISIONS.md`.

### 2. Information design

- [x] Define the core domain terms and relationships.
- [x] Define requirement identity and granularity.
- [x] Define register fields and statuses.
- [x] Define evidence and citation requirements by file format.
- [x] Define rules, findings, and no-findings behaviour.
- [x] Define export, audit-history, and unchanged-proof contracts.

### 3. System architecture

- [x] Map components and end-to-end data flow.
- [ ] Define document parsing and model/provider boundaries.
- [ ] Define run identity, idempotency, and concurrency behaviour. Slice 1's
      share is settled (UUID run id, per-project lock, queued second run);
      the rest arrives with the slice that needs it.
- [x] Define LangGraph state, nodes, edges, and checkpoints.
- [ ] Define database tables, migrations, versions, and audit trail. Slice
      1's share is settled (seven tables, migrations from the first table);
      the rest arrives with the slice that needs it.
- [ ] Define the human-review state machine.
- [ ] Define watched-folder and focused-update architecture.
- [ ] Define prompt-injection, no-bluff, and security controls.
- [ ] Define FastAPI, MCP, and React contracts. Slice 1's share is settled
      (five endpoints); the rest arrives with the slice that needs it.
- [ ] Define failure, retry, logging, timing, and cost behaviour.

### 4. Proof and implementation plan

- [ ] Build the requirement-to-acceptance traceability matrix.
- [ ] Design synthetic projects and the edge-case matrix.
- [ ] Define the no-live-key automated test strategy.
- [ ] Plan implementation slices and repository boilerplate.
- [ ] Plan fresh-clone verification and demo evidence capture.

## Review findings — open

Two independent documentation reviews were run on 2026-08-11 against the same
brief, each reading the task PDF, the working notes, `TASK.md`,
`DECISIONS.md`, `PROGRESS.md`, `README.md`, and the two folder READMEs. The
reviewers were two different models, run separately with no sight of each
other's work:

- **Fable** — background agent inside this repository.
- **Codex** — `codex exec`, run non-interactively.

`[both]` = raised independently by both reviewers · `[F]` = Fable only ·
`[C]` = Codex only.

**Nothing here has been judged yet.** This list records what the reviewers
said and where a fix would land. Real-or-not is decided one at a time before
anything is written. As each finding is resolved, its fix goes to
`DECISIONS.md`, `README.md`, `TASK.md`, or `config/README.md`, and its entry
is removed from here — this section is meant to shrink to nothing.

### How placement was decided

| Destination | What goes there |
|---|---|
| `DECISIONS.md` — text fix | The finding is stale, contradictory, or misattributed text *inside* a canonical section. No new decision needed; the section is corrected in place. If a Decision Log row changes meaning, the old row is marked `SUPERSEDED` and a new dated row is added (append-only rule). |
| `DECISIONS.md` — new decision | Something genuinely undecided. It must be decided first, then written as its own canonical section plus a Decision Log row. |
| `PROGRESS.md` | Tracking only — roadmap ticks, the dated log entry for this review, and any assumption. Never a second decision log. |
| `README.md` | User-facing claims and limitations. |
| `TASK.md` | Standing working rules only. |

Most items land in two places: the fix itself in `DECISIONS.md`, and a
roadmap tick or log line here. Only the non-obvious second destination is
named below.

### Blocking slice 1

#### 1. Model provider and model never decided — `[both]`
Fable S1 · Codex 5.4. Extract is in slice 1 and calls a model; no provider,
no model, no env-var contract anywhere. Codex 3.4 is the same gap seen from
the other end: the "no chunking, ~150-page ceiling" decision rests on a
context window belonging to a model that was never chosen.

**Already decided in conversation on 2026-08-11** — OpenRouter, model name in
`config/model.yaml`, key in `.env`; one client passed to the three stages.
Not yet written into `DECISIONS.md`.

- Lands in: `DECISIONS.md` new section + Decision Log row · `config/README.md`
  gains a `model.yaml` row · this file ticks Phase 3 #2 · `README.md`
  states the key requirement.
- Also settles Codex 3.4 once the chosen model's context window is stated.

#### 2. `POST /runs` has no project or input contract — `[both]`
Fable S3 · Codex 5.1. Slice 1 is "one `.md` file in" with the watched folder
explicitly out of scope, but nothing says how a run learns which project it
belongs to or which folder Ingest reads. Every table is per-project.

- Lands in: `DECISIONS.md` — "API — slice 1" and "Database tables — slice 1"
  extended; needs a decision first.

#### 3. No status value for a first-run row — `[F]`
Fable S2. The five values are `Done` · `Partial` · `Never happened` ·
`Blocked` · `Disputed`. Slice 1's own scenario is one `.md` producing two
fresh rows with no delivery and no testing evidence yet; none of the five is
true of that row, and `Never happened` asserts something the sources do not
say. D2 ("no row marked `Done` without a testing outcome") already assumes
rows exist under some other status before testing.

- Lands in: `DECISIONS.md` — "Register shape" status set; needs a decision.
- Note: statuses are locked as config-changeable, so this connects to item 10.

#### 4. `InMemorySaver` cannot prove kill-and-resume — `[C]`
Codex 2.3. "Orchestration framework decision" says `GenericFakeChatModel`
plus `InMemorySaver` satisfy behaviour #7, while slice 1 lists Postgres and
the kill-and-resume test. An in-memory checkpointer dies with the process, so
it cannot demonstrate behaviour #2.

- Lands in: `DECISIONS.md` — text fix in "Orchestration framework decision";
  possibly a decision about which checkpointer each test class uses.

#### 5. Nothing owns background execution, restart, or the lock lifecycle — `[C]`
Codex 5.2. Three locked statements depend on a mechanism that was never
chosen: `POST /runs` returns immediately and "the work continues in the
background"; one run per project "enforced by a database lock"; a queued run
"starts on its own" when the first commits. After a process kill the
LangGraph checkpoint survives, but nothing says what restarts the run or what
happens to the lock.

- Lands in: `DECISIONS.md` — extends "Run identity and concurrency" and
  "Run state and checkpoints"; needs a decision.

#### 6. Pending proposals and the rejected-export ending have no home — `[C]`
Codex 5.3. Match writes rows that "stay a proposal until Commit", but the
seven tables describe `register_rows` as holding requirements, with no
pending state. Run status runs `waiting → running → waiting for review →
done`, so a rejected export has no terminal transition and no defined moment
where the project lock is released.

- Lands in: `DECISIONS.md` — "Database tables — slice 1" and a new
  human-review state machine section; this file ticks Phase 3 #6.
- This is the point currently under discussion (Phase 3 #6).

### Should fix before submission

#### 7. `TASK.md` mandates the UI shape `DECISIONS.md` rejected — `[both]`
Fable C1 · Codex 3.2. `TASK.md`: *"The review UI stays small. One list, two
buttons."* `DECISIONS.md` "Review interface — scope": *"not a two-button list
either — an earlier sketch of 'a list and two buttons' was too small"*, and
locks one page with four sections. An agent following `TASK.md` would build
the rejected design and drop behaviours #1 and #10 from the screen.

- Lands in: `TASK.md` — "Shape of the system" line corrected to point at the
  locked decision.

#### 8. Intra-file delta processing rests on undecided version retention — `[both]`
Fable B3 · Codex 3.3. "Incremental input contract" locks that *"only the
changed part of an edited file is processed"*, then says retaining the earlier
version is architecture-phase work. Lock 2a meanwhile says *"Documents read
in-place — no copy, no upload."* Fable notes the retained extracted text in
the `documents` table may already satisfy this without copying files, but
nothing says so.

- Lands in: `DECISIONS.md` — "Incremental input contract" and Lock 2a
  reconciled; this file's Phase 3 #7 (watched folder / focused update).
- Related to item 11, which is the same sentence seen as a misattribution.

#### 9. Re-running after a `rules.yaml` edit dies at Ingest — `[F]`
Fable C2. "Run identity and concurrency" rejects content-derived run ids
partly on this case: *"change `rules.yaml` and deliberately re-run — content
is identical, so the run would be refused for no good reason."* But "Pipeline
stages" locks the exit *"Ingest | Nothing new or changed | Run ends here"* —
so that same re-run ends before Examine ever runs. Tuning R3's `max_days` is
the most likely real instance.

- Lands in: `DECISIONS.md` — the two sections reconciled; may need a decision
  about what a rules-only re-run does.

#### 10. Three values are locked as "config" with no config file — `[F]`
Fable B2. Status set (*"Adding one is a config edit, never a code change"*),
citation quote length (*"A maximum length lives in config"*), and the
document page limit (*"Document size limit lives in config"*) all promise a
config home. `config/README.md` lists only `rules.yaml` and `formats.yaml`.
Configuration-over-code is a graded requirement (task PDF page 12).

- Lands in: `config/README.md` plus whichever config files are chosen;
  `DECISIONS.md` names them.

#### 11. Intra-file delta is credited to the brief — `[F]`
Fable M1. `DECISIONS.md`: *"only the changed part of an edited file is
processed, never the whole document again. This half is the brief's own
requirement — task PDF page 2."* The PDF actually says: *"Each arrival
produces a focused update to the deliverable, not a rewrite and not a full
re-run that happens to reproduce the same bytes; an update should cost like an
update."* That constrains the deliverable and the run cost, not the reading of
one edited document. `TASK.md` forbids writing "the brief says" where the PDF
does not.

- Lands in: `DECISIONS.md` — "Incremental input contract" text fix.

#### 12. The gate rule and its own table disagree — `[C]`
Codex 2.1. Rule: *"the gate applies where the system is making a judgement or
changing something that already exists."* Table row 2: *"New evidence added to
an existing row, same meaning | No | Same fact, more proof; nothing changed."*
Adding a citation does change an existing row.

- Lands in: `DECISIONS.md` — "Human-gate scope" text fix or a narrowed rule.

#### 13. Reject means two different things — `[C]`
Codex 2.2. Global: *"Reject = excluded from the register, kept in the run
record, permanently"* and *"Reject stops it."* But for an uncertain match the
table says *"Reject | Two separate rows"* — which creates register content
rather than excluding it.

- Lands in: `DECISIONS.md` — "Human-gate actions" text fix.

#### 14. README claims format support that does not exist yet — `[C]`
Codex 2.4. README marks `.pdf` `.docx` `.md` `.txt` as ✅ Supported, while
this file says *"No code yet in this repository"* and the relevant
`DECISIONS.md` evidence is reasoning-stage. Behaviour #5 says a success claim
must match the real state.

- Lands in: `README.md`.

#### 15. The `In writing? = No` cell cannot satisfy the citation contract — `[C]`
Codex 2.5. Citations are locked as *"Three parts: file · place · the words
themselves"* on every cell, but the worked example for an absence is
*"`client-requirements-v1.md` read in full, no mention of search"* — no place,
no quoted words. R1, the rule this system exists for, depends on exactly this
cell.

- Lands in: `DECISIONS.md` — "Citations" and "Register shape" reconciled;
  may need a decision on how an absence is cited.

#### 16. The deliverable section still calls locked things open — `[C]`
Codex 3.1. "Deliverable shape" ends: *"Exact columns, statuses, row-matching
behaviour, review actions, UI presentation, storage, and export format remain
open for their own decision blocks."* All of those except UI presentation
were locked later the same day.

- Lands in: `DECISIONS.md` — text fix.

### Minor

#### 17. The citation locator assumes a quote appears once — `[C]`
Codex 3.5. *"the code searches the document text for those words and derives
the page, heading, or line itself"* and *"a wrong one is not possible."* A
requirements document repeating the same sentence in scope and in acceptance
criteria would return the first match, which may be the wrong place.
Judge whether this is real in this domain before acting.

- Lands in: `DECISIONS.md` — "Extract — how documents are read", either a
  qualified claim or a stated limitation.

#### 18. Lock 2a claims per-file checkpoints the later lock removed — `[F]`
Fable C3. Lock 2a: *"Kill-resume covers every document boundary via the
checkpointer."* "Run state and checkpoints": *"Ingest, per file … No — rerun
the whole stage … Ingest is therefore a single node with no internal
checkpoint."* Lock 2a predates the six-stage pipeline and was never
reconciled.

- Lands in: `DECISIONS.md` — Lock 2a text fix.

#### 19. A column name that does not exist — `[F]`
Fable C4. "Requirement identity": *"which is how First appeared and What
testing found both get filled on a single row."* "Register shape" has
`First seen`, not `First appeared`.

- Lands in: `DECISIONS.md` — text fix.

#### 20. A quote from the working notes that is no longer there — `[F]`
Fable B1. "Review interface — scope": *"The working notes say a human can
'approve, reject, modify, or resolve' a finding."* The notes now say the
opposite — *"Human har finding ko approve ya reject kar sake (page 2 — bas
yahi do)"*. The Decision Log follow-up inherits the same dead pointer.

- Lands in: `DECISIONS.md` — text fix.

#### 21. LangGraph is called the founder's stack — `[F]`
Fable M2. `DECISIONS.md`: *"The brief names LangGraph as the founder's own
working stack"*, and AutoGen/CrewAI *"would need a deviation justification"*.
The PDF page 3 says *"an agent orchestration framework such as LangGraph or
LangChain"* and *"Comparable tools count as comparable: AutoGen, CrewAI, or a
hand-rolled agent loop are all legitimate choices."* The LangGraph choice
stands on its other reasons; this particular reason does not.

- Lands in: `DECISIONS.md` — "Why LangGraph" text fix.

#### 22. The spreadsheet rail is cited backwards — `[both]`
Fable M3 · Codex 4.3. Lock 2a: *"spreadsheets are out. Acceptable — task PDF
page 8 rails spreadsheet-output products out anyway."* The PDF says *"We are
not building spreadsheet editing. Reading a spreadsheet as a source is fine;
a product whose output is an edited spreadsheet is not."* Excluding `.xlsx`
input is a fine own choice; the PDF is not support for it.

- Lands in: `DECISIONS.md` — Lock 2a text fix.

#### 23. README owes the default `rules.yaml` note — `[F]`
Fable B4. "Rules and playbook": *"The repo ships a filled-in `rules.yaml` so a
fresh clone actually runs … README must state this explicitly."* The README
does not mention rules at all, while every other README obligation from the
same date was added.

- Lands in: `README.md`.

#### 24. Two opposite conflict rules both attributed to the PDF — `[C]`
Codex 4.1. "Human-gate scope": *"The brief's own rule: surface both sides, the
human chooses."* "Human-gate actions": *"Choosing a side would be resolving
it, which the brief forbids."* The PDF says only *"the conflict is surfaced,
not silently resolved"* and *"Conflicts, findings, and updates are approved or
rejected by a person before they commit."* It neither requires nor forbids the
human picking a side. Our own position may be right; the attribution is not.

- Lands in: `DECISIONS.md` — both sections' text fixed.

#### 25. A declared type list is not the "fixed script" the PDF warns about — `[C]`
Codex 4.2. Lock 2b: *"a hardcoded type list is exactly the 'fixed script with
labels' the task PDF warns against."* The PDF: *"One model call wrapped in a
user interface is not an agentic system, and neither is a fixed script with
labels"* — that sentence is about orchestration, not about declaring accepted
input types.

- Lands in: `DECISIONS.md` — Lock 2b text fix.

### Coverage gaps both reviewers noted

#### 26. Behaviour #6 — one documented command — neither decided nor cut
Codex marks it unaddressed: `TASK.md` Commands still reads *"Setup: TBD / Run:
TBD / Test: TBD"*, and this file's "Decide coverage or defended cuts for
behaviours 6–10" is unticked. The PDF (page 3) allows 6–10 to be cut **with a
stated reason**; nothing is stated either way. Fable reads the same facts as
"deferred to build time, logged" rather than a defect.

- Lands in: `TASK.md` Commands once code exists; tracking here.

#### 27. Behaviours #4 (MCP) and #8 (prompt injection) are intent, not decisions — `[F]`
Both are floor behaviours (1–5 cannot be cut). MCP exists only as four tool
names inside "Orchestration framework decision"; the injection detector exists
as a design note and is out of slice 1. Codex reads both as addressed.
Reviewers disagree — worth resolving.

- Lands in: `DECISIONS.md` when their slices arrive; tracking here meanwhile.

## Assumptions

Append-only. An assumption that turns out wrong stays on the list and gets
marked — the correction is more useful than a clean page.

| Date | Assumption | Why we assumed it | Status |
|---|---|---|---|
| 2026-08-09 | The register stays small — roughly 15 rows, ~250 tokens | Basis for rejecting an embedding shortlist in requirement matching; the whole register fits in one model call, so nothing needs narrowing | Register now chosen — seven columns, `DECISIONS.md` "Register shape", 2026-08-11 — still open until measured against real sample projects |
| 2026-08-09 | Source documents are short enough to read whole | Meeting notes, client requirements documents, and testing feedback are expected to be short, so vector retrieval may not be needed | Open — if real documents turn out large, pgvector retrieval comes back in |
| 2026-08-11 | Source documents run 5–10 pages (40–50 would already be unusual) | The domain is small teams and freelancers | A config page-limit plus a stated README limitation cover documents beyond it — chunking was therefore not built |

## Blockers

_None open._

## Log

Newest first.

**2026-08-11 — Two independent documentation reviews run; 27 findings recorded**
Two models, Fable and Codex, reviewed the repository documentation separately
against the same brief, with no sight of each other's work. Their findings are
merged into "Review findings — open" above: 6 blocking slice 1, 10 to fix
before submission, 9 minor, and 2 coverage gaps. Five were raised by both
reviewers independently. Nothing has been judged or fixed yet; each is decided
one at a time, and its entry is removed once its fix lands.

**2026-08-11 — Phase 3 architecture: pipeline, state, run identity, database tables, and API locked**
Locked in `DECISIONS.md`: the six pipeline stages (Ingest through Commit)
with where the model is called, Extract's one-document-per-call shape with
its citation/fabrication-detector mechanism, Match and Examine kept
separate, LangGraph state-vs-database and checkpoint placement, run
identity's slice-1 share (UUID, per-project lock, one queued waiting run),
the seven slice-1 database tables, and the five slice-1 API endpoints.
Deliberately partial — five Phase 3 points remain untouched. Rewrote the
stale closing line in "One-run scope" to point at the new run-identity
section. Added three README limitations (R3 timing, one-run-per-project
queueing, the document size limit).

**2026-08-11 — Vocabulary locked; consistency-audit backlog cleared**
Renamed `request` → `requirement` and `pile` → `project` throughout
`DECISIONS.md`, `TASK.md`, and `PROGRESS.md` (`batch` was already its own
word and stays untouched); Decision Log rows, `documentation/`, and the
frozen review-screen mockup keep the old words on purpose. Added
`DECISIONS.md`'s `## Vocabulary` section, the canonical home `TASK.md`
pointed at but that never existed, and fixed the pointer. Renamed
`sample-piles/` to `sample-projects/` (plain `mv`, no git
history) and rewrote its README, which had called a project's whole folder
"what a single run consumes" — that is a batch. Resolved and removed six
audit items: citation-preserving extraction, the classify-stage remnant,
`request`/`requirement` drift, the vocabulary-home gap, `pile`/`batch` drift,
and the status-label mismatch; the short-document/pgvector assumption stays
open. Superseded the 2026-08-09 "deliberately hardcoded" accepted-format-list
row: the list now lives in `config/formats.yaml`, the readers stay in
`app/ingest/`, and a startup check reconciles the two — new Decision Log row
added. Banner-marked the review-interface mockup as superseded (stale
`classify` stage, `Delivered` status, per-row `[✓][✗]`); the redesign itself
stays deferred to the architecture phase, not done now. Corrected the
working-notes coverage-index date. Added the reject-suppression limitation
and the run-trigger assumption to `README.md`, and a rule to `TASK.md` on
what actually earns a `DECISIONS.md` entry.

**2026-08-11 — Phase 1 and Phase 2 closed**
Locked the remaining decisions in `DECISIONS.md`: human-gate actions
(Approve/Reject, reject kept permanently in the run record), the incremental
input contract (batch = every new and changed file waiting when a run
starts), the seven-column register shape with per-cell citations and five
status values, citation format per file type, and export/audit-history/
unchanged-proof. Ticked the incremental-input-contract item and all six
Phase 2 items; the three remaining Phase 1 items are logged as deferred to
build time, not cut. D2 now reads `Done`, which resolves and removes the
"D2 depends on an unlocked status" audit bullet above. Added three working
rules to `TASK.md`.

**2026-08-11 — Human-gate scope locked**
Locked the 13-scenario human-gate checklist in `DECISIONS.md`: gated wherever
the system judges or changes an existing row, not where it only copies a fact.
Ticked the product-contract checklist item and queued one more
consistency-audit entry — the review-screen mockup's per-row `[✓] [✗]`.

**2026-08-11 — Consistency audit widened (housekeeping only)**
Recorded six further unresolved issues found during a read-only context audit:
four terminology or dependency drifts, one stale coverage index, and the mismatch
where several 2026-08-09 decisions read as locked in `DECISIONS.md` while their
information-design counterparts here are still open. Nothing was resolved and no
product decision changed. Also corrected the project auto-memory, which still
claimed scoping was complete and carried the superseded domain and run-scope
wording.

**2026-08-11 — Documentation handoff hardened**
Added an append-only decision-history policy, restored superseded decisions,
removed the conflicting old run-scope section, and added root Claude Code
continuation instructions. Added permanent cross-agent rules for verifying
memory, separating fact from inference, and asking when material evidence is
missing. No product behaviour changed in this cleanup.

**2026-08-11 — Domain corrected; register selected**
Replaced the previous software-feature-delivery framing with the agreed
Software Requirements-to-Delivery contract across `README.md`, `TASK.md`, and
`DECISIONS.md`. Selected the Requirements-to-Delivery Register after comparing
it with a brief and report; queued six consistency issues for their relevant
decision blocks before architecture begins. Added the four-phase planning
roadmap so another agent can continue from the exact next decision. Locked one
provider-side Delivery Owner as both system user and human reviewer for V1.
Separated the continuing project register from individual initial and update
runs, and locked one run as one complete document-batch processing cycle.

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
