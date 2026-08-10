# DECISIONS.md

Every call made while building this system, and the reasoning behind it.

This file answers **"what did we choose, and why?"** The task brief itself —
what the founder actually asked for — is interpreted separately in
`documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`. Keep the
two apart: their requirements there, our choices here.

Every entry records the same eight things:

**Decision** what was chosen · **Problem** what it solves · **Alternatives**
what else was on the table · **Reason** why this one · **Trade-off** what was
given up · **Evidence** the test, measurement, or demo that backs it ·
**Limitation** where it is weak · **Next improvement** what would make it
better with more time.

Rejected alternatives are written down deliberately so they do not resurface.

**Nothing here is a claim of evidence.** Where an entry says the reasoning is
untested, it is untested — those must be upgraded to real evidence before the
write-up repeats them.

---


## Decision Log
| Date | Decision | Reason | Trade-off | Proof / Link | Follow-up |
|---|---|---|---|---|---|
| 2026-08-09 | Agent orchestration = **LangGraph** (raw `StateGraph` for Task 1); LangChain only as thin `langchain-core` layer; no legacy chains/`AgentExecutor` | Brief behaviours #1, #2, #3, #9 are LangGraph built-ins; it is the founder's own named stack, so zero deviation cost; checkpointer shares our existing PostgreSQL | More boilerplate than a hand-rolled loop; real learning curve; still leaves ~5.5 of 10 behaviours for us to build | Research-stage only — see "Orchestration framework decision" section | Convert to real evidence via resume test, same-pile concurrency test, and stage-timing numbers before write-up |
| 2026-08-09 | Task 2 orchestration shape (`create_agent` vs `StateGraph`) **deferred** | `create_agent` runs on the LangGraph runtime, so deciding later is not a rewrite; Task 1 is the current focus | Task 2 stack stays formally open a while longer | — | Decide when Task 2 starts, against the SuperDocs four-call contract |
| 2026-08-09 | Task 1 deliverable = **register (table)**, not a narrative brief/report | A row is a natural unit of change, so incremental-update invariance is provable; prose is not | Less nuance than prose; mitigated by a thin header + conflicts section around the table | Reasoning-stage — needs an incremental-update test | Prove unaffected rows stay byte-identical |
| 2026-08-09 | Accepted formats = **`.pdf`, `.docx`, `.md`, `.txt`** (hardcoded gate) | These are the shapes real project documents arrive in; `.eml` parsing adds cost with no evaluation gain | Images and spreadsheets excluded | — | Declare the list in README (task PDF page 4) |
| 2026-08-09 | Unrecognised document types → **three-bucket handling** (known / related-unknown / unrelated), decided at runtime | A hardcoded type list would be the "fixed script with labels" the task PDF warns against | Bucket-2 docs yield lower-confidence facts | — | Second-run test must include one bucket-2 and one bucket-3 file |
| 2026-08-09 | Domain = **Software feature delivery**; no industry named; contracts/SOW/invoices excluded | Aditya's lived Arka experience; sits inside the task PDF's own example list; industry-free so the evaluator's second-run pile still fits | Loses the immigration-vertical tie-in that would have echoed Task 2 | — | Lock the document-type list next |
| 2026-08-09 | Document types = **3** (meeting notes, feature request list, testing feedback). Email thread, internal spec, and delivery note all **cut** | Each surviving type feeds a distinct register column; the cut three were either redundant or never existed at Arka | Fewer types to demo; relies on bucket-2 handling if an evaluator's pile has an extra type | — | Build synthetic pile with ~9 files across the 3 types |
| 2026-08-09 | Blockers = a **status + column**, not a document type | A blocker is a state a request sits in; its record already lives in meeting notes | One extra column to populate | — | Blocked rows must produce a "stalled, never followed up" finding |
| 2026-08-09 | Request identity = **model matches candidate against the whole register; no embedding layer**. Uncertain → flag, never merge | Register is ~250 tokens, so nothing needs narrowing; an embedding shortlist would add a silent-miss failure mode for no gain | Cost grows with register size — fine at this scale, revisit if a pile ever produces hundreds of rows | v1 starting point, no build evidence yet | Re-examine after the first real run; if vector retrieval ends up unused anywhere, defend that in the write-up |
| 2026-08-09 | Request granularity = **the source document's own cut**; one written item = one row | Re-cutting the customer's list would be our judgement, not a fact in any document — violates the locked facts-not-judgements rule | A bundled bullet becomes one broad row | v1 starting point | Bundle-detection flag is parked, not built; revisit after the first real pile |
| 2026-08-09 | **One run = one project**; run starts with a project identifier + folder; out-of-project docs → bucket 3 | Task PDF page 2 assumes *related* documents; mixing projects would corrupt matching and the register; gives bucket-3 decisions a concrete yardstick | Cannot analyse two projects in a single run | — | Idempotency now keys on the project identifier — design and test it |
| 2026-08-09 | **Review interface scope** — one page, four sections (stages · skipped · register · cost) | Behaviours #1 and #10 land on this screen too, not just #3; an earlier "list and two buttons" sketch was too small | More UI than planned, though still one screen | — | `modify`/`resolve` are beyond the brief — optional only |
| 2026-08-09 | **Build order = vertical slices**, riskiest property first, interface last | Every graded behaviour is a runtime property and cannot be exercised on a dummy-data scaffold | Interface risks being rushed at the end | — | Slice 1 must prove kill-and-resume before anything widens |
| 2026-08-09 | **Repository layout** — runnable things at the root, background under `documentation/`; three folders renamed | A stranger must understand the tree from the root listing alone (behaviour #6); the old names would have misled readers | Empty `app/`/`ui/`/`tests/` exist before any code | — | Fill them as code arrives |
| 2026-08-09 | Rules live in a user-supplied **`rules.yaml`**, with a filled-in default shipped in the repo; **4 rules locked** (R1–R4) | Task PDF page 2 says the user hands over the rules; page 12 requires a new rule to be a data change; a default file is needed for behaviour #6 (fresh clone runs) | Four rules cover less ground than a long list, but each can actually be demonstrated | — | Prove rule-file swapping in the demo |
| 2026-08-09 | Finding = **5 required fields** (rule, found, evidence, row, decision) + review state | Evidence field satisfies the exact-source requirement; decision field keeps the human gate real; review state enables mixed approve/reject in one session | Rigid shape; a finding that fits none of the fields has nowhere to go | — | Watch for findings that resist the shape during build |
| 2026-08-09 | **D1/D2 deliverable-side rules** — every row cites a source; no `Delivered` without a testing outcome | Task PDF page 2 requires checking the deliverable too; these catch the system's own bad output, not just bad documents | Two extra checks per run | — | Must be covered by tests |
| 2026-08-09 | `No findings` is a **first-class output** — never manufacture, never render as a blank/crash | Task PDF page 2 calls an honest no-findings report the rarest output; behaviour #5 requires success messages to be true | — | — | Needs a test asserting a clean corpus yields zero findings and a non-empty message |
| 2026-08-09 | PDF extraction = **pdfplumber** (primary) + **pypdf** (encryption check only); scanned and encrypted PDFs skipped with reason | pdfplumber preserves table structure; pypdf adds one-line `.is_encrypted`; two libraries, two jobs, zero overlap | 300 KB extra dependency (pypdf); no scanned PDF support | Tested on 7 PDFs including 59-page IRS doc (14 tables, 315K chars) and 22-page MSA — zero data loss across all pages | Add OCR only if domain expands to scanned documents |

---

## PDF library choice — pdfplumber + pypdf (LOCKED 2026-08-09)

- **Decision:** `pdfplumber` for extraction, `pypdf` for encryption detection only. Scanned/encrypted PDFs skipped with reason.
- **Date locked:** 2026-08-09.
- **Problem:** PDF hardest of four formats — tables, encryption, scanned pages need deliberate choices.
- **Alternatives:** pdfplumber alone (crashes on encryption, empty error message), pypdf alone (garbles tables), pdfminer directly (lower-level internal API, 6 lines instead of 1).
- **Reason:** pdfplumber preserves table structure (rows × cols). pypdf's `.is_encrypted` is a one-line, well-tested public API. Two libraries, non-overlapping jobs.
- **Trade-off:** 300 KB extra dependency (pypdf). No scanned PDF support — OCR (`pytesseract`) rejected: adds system-level Tesseract dependency, slows processing, unnecessary in this domain.
- **Evidence:** Tested 7 PDFs on 2026-08-09: 59-page IRS doc (14 tables, 315K chars), 22-page MSA (5 tables), 21-page MSA, 14-page task PDF, IRS W-9 form, encrypted synthetic (detected), scanned synthetic (0 chars, flagged). Zero pages empty. All tables structured.
- **Limitation:** Scanned PDFs → 0 chars → skipped. Multi-column layouts → best-effort, may garble ordering in edge cases.
- **Next improvement:** OCR if domain expands to scanned docs. Column-ordering heuristics if real piles surface garbling.

## Orchestration framework decision — LangGraph (LOCKED)

### Decision record
- **Decision:** LangGraph is the agent-orchestration runtime for Task 1. LangChain is used only as a thin layer underneath it (model wrappers + tool definitions via `langchain-core`), never as the orchestration layer itself.
- **Date locked:** 2026-08-09.
- **Problem it solves:** Task 1's brief demands four behaviours that are all runtime-level state problems: watchable branching stages, kill-and-resume, an item-by-item human gate, and non-corrupting concurrent runs. These are the expensive, bug-prone parts of any agentic system.
- **Alternatives considered:** LangChain-only (no LangGraph), hand-rolled agent loop, AutoGen, CrewAI. All four are explicitly permitted by the brief ("Comparable tools count as comparable," Task PDF page 3).
- **Reason chosen:** See "Why LangGraph" below.
- **Trade-off accepted:** More boilerplate than a hand-rolled loop for simple linear work, and a real learning curve (framework docs describe it as "very low-level"). Accepted because Task 1's flow is genuinely branching, not linear.
- **Evidence:** ⚠️ Research-stage only as of 2026-08-09. No build evidence yet. Must be upgraded to real evidence (resume test, concurrency test, timing numbers) before the write-up claims any of this.
- **Limitation:** LangGraph covers roughly 4.5 of the brief's 10 behaviours. The remaining ~5.5 are our own design and discipline. Full ownership split below.
- **Next improvement:** Once the graph exists, revisit whether Task 2 reuses the same StateGraph or takes the higher-level `create_agent` path (see "LangChain usage boundary").

### Framework relationship — not an either/or
LangChain and LangGraph stopped being competing choices at their joint 1.0 release (22 Oct 2025). Current shape:
- **LangGraph** = the low-level runtime: state machine, checkpointing, durable execution, human-gate primitives.
- **LangChain** = the convenience layer on top: model/tool abstractions, `create_agent`, middleware.
- LangChain's `create_agent` is itself built on the LangGraph runtime — choosing it is not an alternative to LangGraph, it is a higher abstraction level over the same engine.

Therefore the real question was never "which framework" but **"how low do we go."** Answer: Task 1 goes low (raw `StateGraph`), because its flow is not the standard model-calls-tools-in-a-loop shape.

**Version facts (as of 2026-08-09):** `langgraph` latest stable 1.2.10 (28 July 2026); 1.x series, so API-churn risk is low for the submission window.

### Why LangGraph — mapped to the brief's own words
These four brief behaviours map directly onto LangGraph built-ins:

| Brief behaviour (Task PDF pages 2–3) | LangGraph feature that provides it |
|---|---|
| #1 "works in steps we can watch… decisions must be able to change the path" | `StateGraph` nodes + conditional edges |
| #2 "survives being stopped… continues from where it left off" | Checkpointer / durable execution |
| #3 "a human holds the gate… item by item" | `interrupt()` + `Command(resume=...)` |
| #9 "two runs at the same time stay two runs" | `thread_id` isolation + Postgres checkpointer (multi-worker safe) |

Supporting reasons:
- **Zero deviation cost.** The brief names LangGraph as the founder's own working stack. Building in it means our work is directly comparable to the job, and the write-up spends no words defending a deviation.
- **One database.** `langgraph.checkpoint.postgres` puts checkpoints in the PostgreSQL instance we already need for pgvector retrieval. No second datastore, no second failure mode.
- **Small explainable concept surface.** Six concepts total: State, Node, Edge, conditional edge, Checkpointer, interrupt. This matters because the founder may modify the build live — every concept must be defensible out loud without notes.
- **Testable without a live key.** `GenericFakeChatModel` (scripted responses, including tool calls and errors) plus `InMemorySaver` satisfy the brief's behaviour #7 requirement that tests run without spending money.
- **Stage boundaries come free.** Because work is already partitioned into nodes, per-stage timing for behaviour #10 is a start/end stamp per node. In a monolithic loop the concept of a "stage" does not naturally exist, so the required breakdown would be artificial.

### Why the alternatives were rejected
- **Hand-rolled agent loop:** would mean re-implementing checkpointing, resume semantics, and run isolation ourselves — i.e. writing a worse LangGraph with far less testing behind it. Time spent there buys no evaluation credit; the brief grades the four behaviours, not their implementation origin.
- **LangChain-only (no LangGraph):** LangChain's single-pass chain model has no durable state or resume story. Behaviour #2 alone rules it out.
- **AutoGen / CrewAI:** both are permitted, but neither is the founder's stack, and both would need a deviation justification in the write-up for no functional gain on the four behaviours above.

### LangChain usage boundary — what we deliberately do NOT use
This is an explicit guardrail, not a preference. LangChain's older surface area is large and much of it is legacy.

- ✅ **Allowed:** `langgraph`, `langchain-core` (message types, tool definitions), and exactly one model-provider package.
- ❌ **Not allowed in Task 1:** legacy `Chain` classes, `LLMChain`, `AgentExecutor`, and any other pre-1.0 orchestration abstraction. These are deprecated-era constructs; using them would both bloat the dependency tree and undercut the "we chose the runtime deliberately" story.
- ⏸️ **Deferred to Task 2:** LangChain's `create_agent` + middleware (`HumanInTheLoopMiddleware` etc.). Task 2 (RFE builder, S3 band) is small and bounded, so the high-level path may fit better there — but that call is **not being made now**. Because `create_agent` runs on the LangGraph runtime anyway, deciding later costs nothing and is not a rewrite.
- **Current focus is Task 1 only.** Task 2's orchestration shape gets decided when Task 2 starts, against the actual SuperDocs four-call contract (upload / chat / approve / export).

### Behaviour ownership split — what the framework does NOT give us
Honest accounting across all ten brief behaviours. This table is the antidote to assuming a framework choice covers the requirements.

| # | Brief behaviour | LangGraph gives | We build |
|---|---|---|---|
| 1 | Watchable stages, decisions change path | ✅ Full | Stage definitions and routing logic |
| 2 | Survives being stopped | ✅ Full | Checkpoint granularity choice; resume test |
| 3 | Human holds the gate | ✅ Full | Findings schema; per-item decision handling |
| 4 | A machine can drive it | ❌ None | **Entire MCP server** (FastMCP) |
| 5 | It never bluffs | ❌ None | **Entire design** — schema + prompt discipline |
| 6 | A stranger can run it | ❌ None | **Entire repo hygiene** — docker-compose, README, seed data |
| 7 | It proves itself | 🟡 Half | Fake model + InMemorySaver are given; **the tests are ours** |
| 8 | Takes no orders from documents | 🟡 Marginal | **~90% ours** — data/instruction separation + detector |
| 9 | Concurrent runs stay separate | ✅ Mostly | Same-pile duplicate-run strategy (see risk below) |
| 10 | It knows what it cost | 🟡 Half | Token counts via `usage_metadata`; **stage timing + cost roll-up ours** |

**Summary: LangGraph covers ~4.5 of 10; ~5.5 are ours.** That split is acceptable because the 4.5 it covers are the hardest and most failure-prone (durable state, resume, isolation), while what remains is mostly design discipline rather than infrastructure.

Also entirely ours, outside the ten behaviours: the watched-location intake + incremental-update logic, and pgvector retrieval.

### Design notes for the behaviours LangGraph will not help with
- **#4 (MCP):** LangGraph gives no MCP server, but its design makes ours thin. The graph is already driven by `thread_id` rather than by HTTP session, so MCP tools (`start_run`, `get_status`, `list_findings`, `approve`) become wrappers over `invoke` / `resume`. A hand-rolled loop would have required inventing that run-addressing model first.
- **#5 (no bluffing):** enforce structurally, not by prompting. Findings use a schema where `evidence` cannot be empty — no evidence location, no finding. Success states are emitted only after the durable operation actually completes.
- **#8 (prompt-injection resistance):** document text never enters a system-instruction slot; it is always passed as a data field. Add a detector that turns instruction-like content in a source document into a reported finding rather than a followed command. Both #5 and #8 need explicit tests — the brief asks for exactly these.
- **#10 (cost/time):** per-node start/end timestamps rolled up per run, plus `usage_metadata` token counts converted to an estimated cost. Report tail behaviour and variance, not just an average (brief's measurement standard).

### Known risk to test and disclose
Behaviour #9 has two distinct cases, and LangGraph only covers one of them:
- **Different piles, different `thread_id`** → handled cleanly; the Postgres checkpointer is multi-worker safe. ✅
- **The same pile started twice** → **not** handled automatically. Needs our own idempotency key or DB-level lock.

This second case must be explicitly tested and documented in the README. Surfacing it is the "proof over assertion" behaviour the brief rewards; leaving it implicit would be the kind of untested claim it penalises.

---

## Deliverable shape — register/table (LOCKED 2026-08-09)

- **Decision:** Task 1's grounded deliverable is a **register** — a table where one row tracks one item — not a narrative brief or report.
- **Problem:** The brief offers three shapes ("a register, a brief, or a report", Task PDF page 2) and we must pick one before designing state, extraction, or the review UI.
- **Alternatives:** narrative brief, narrative report. Both explicitly permitted by the brief.
- **Reason:** Driven by the brief's *incremental update* requirement (page 2) — when a new document arrives, unaffected output must stay **exactly** as it was and the system must be able to **prove** it. A row is a natural unit of change: new document → 2 rows change, the rest stay byte-identical, provable by row-level hash comparison. Narrative prose has no such unit — an LLM rewrite perturbs wording in untouched paragraphs, making invariance almost impossible to prove.
- **Trade-off:** A table carries less nuance than prose. Mitigated by wrapping the table in a thin document: short header (project, documents read, run metadata) → the register table → a conflicts section. The table remains the core.
- **Evidence:** Reasoning-stage. Must be proven by an actual incremental-update test showing unaffected rows unchanged.
- **Limitation:** If a finding genuinely does not fit a row shape, it will be forced into the conflicts section rather than the table. Watch for this during build.
- **Next improvement:** Revisit only if the row model actually breaks in practice; do not pre-optimise.

**Output flow:** documents → system builds register → human reviews row by row (approve / reject) → approved register exported.

The register's final column set is defined once, under "Register — final shape" below. Do not restate it here.

## Domain — Software feature delivery (LOCKED 2026-08-09)

**Declared domain (this exact line goes in the README):**

> **Software feature delivery** — the documents a development team and its customer produce while a feature is requested, built, tested, and changed.

- **Why this domain:** it is Aditya's lived experience as founding engineer at Arka (3-person team building software for immigration legal firms: feature request → build → client testing → change loop). Task PDF page 2 requires a domain the candidate "actually knows and can stand behind," and lists *"a project's plans with its status reports and meeting notes"* among its own examples — this pile is exactly that. The domain is not invented; it sits inside the task PDF's own example set.
- **Naming choices, deliberate:**
  - "feature delivery" not "project delivery" — *project* reads as one-off gig work; *feature* reads as ongoing product work.
  - "customer" not "client" — *client* carries an agency flavour; *customer* is product-neutral.
  - No "small team" qualifier — it diminishes the work for no accuracy gain.
  - **No industry named.** Not "immigration" or "legal". If the domain were bound to an industry, the evaluator's second-run pile (likely some other industry) would fall outside the declared set. The domain is defined by the *work*, not the vertical, so it covers both agency and in-house product teams.
- **Defence line if asked why this domain:** "I was founding engineer at Arka. We built software for immigration legal firms — their feature requests came in, I built them, they tested, then the change loop ran. I saw this pile every day, and the problem was that nothing tracked what was asked for versus what got built."
- **Framing rule:** company-level = "we built software for legal firms"; personal level = "I built their feature requests." Never describe it as client projects or freelancing — it was a company with founders, ongoing customers, and a full build-test-deploy cycle.
- **Out of scope on purpose:** contracts, SOWs, invoices, and pricing documents. Aditya did not own these at Arka and could not defend them under questioning. Anything not lived is not in the pile.

## Declared set — file formats and document types (LOCKED 2026-08-09)

Terminology, kept separate on purpose (conflating these caused real confusion once):
- **File format** = can the file be opened? (`.pdf`, `.docx`, `.md`, `.txt`) — a parsing question.
- **Document type** = what is inside it? (meeting notes, feature request, testing feedback) — a meaning question.

Every incoming file passes two checks, in order: **format first, then type.** A format failure stops before the type check ever runs.

### Lock 2a — accepted file formats
- **Accepted:** `.pdf`, `.docx`, `.md`, `.txt`. Anything else is skipped with reason `unsupported format`.
- **Reason:** these are the shapes real project documents actually arrive in. Email threads are represented as `.txt`/`.md` files rather than `.eml`, avoiding mail-parsing complexity for no evaluation gain.
- **Trade-off:** images/screenshots and spreadsheets are out. Acceptable — task PDF page 8 rails spreadsheet-output products out anyway, and screenshots carry no extractable claim text.
- **This list is deliberately hardcoded.** Task PDF page 12 permits this: intentional hard-coded defences alongside intelligent logic are a legitimate fix, not a patch. Intelligence belongs in the type decision, not the format gate.
- **README must declare this list** — task PDF page 4 requires the accepted formats and domains to be stated, because a second run means different documents inside the declared set.
- **PDF extraction:** `pdfplumber` (text + table extraction) with `pypdf` for encryption detection only. Scanned PDFs and encrypted PDFs are skipped with a message naming the reason and the fix. Full decision and evidence in the PDF library choice section below.

### Lock 2b — unrecognised document types (three-bucket handling)
When a file opens successfully, the system decides — it is not matched against a hardcoded filename list:

| Bucket | Condition | Action |
|---|---|---|
| 1. Known type | Matches one of the declared document types | Process fully |
| 2. Related, unknown type | Belongs to this project, but is a type we did not declare | Extract facts, flag as `unrecognised document type` |
| 3. Unrelated | Not about this project at all (e.g. a resume) | Skip, with the reason recorded |

- **Alternatives rejected:** (A) strict — process only the declared types, skip everything else. Rejected: a hardcoded type list is exactly the "fixed script with labels" the task PDF warns against on page 2. (B) open — attempt to process anything. Rejected: irrelevant files would pollute the register.
- **Reason for the middle path:** the classification decision is made by the system at runtime, satisfying task PDF page 12 ("intelligence in the system deciding, code executing"), while the format gate stays deterministic.
- **Evidence:** must be proven by a second-run test using a different pile that deliberately contains one bucket-2 and one bucket-3 file.

---

## Document types — the declared list (LOCKED 2026-08-09)

Three types. Each one feeds a **different** register column — that is the test a type must pass to earn its place. Two types filling the same column would mean one is redundant.

| # | Document type | What is inside | Register column it feeds |
|---|---|---|---|
| 1 | **Meeting notes** | What was discussed with the customer; what they said verbally | *First appeared* — and specifically the case where a request exists **only** verbally |
| 2 | **Feature request list** | The customer's written list of what to build | *Request* itself + *In writing? ✅* |
| 3 | **Testing feedback** | What the customer reported after testing | *What testing found* |

**Three types is not thin.** A pile is made of files, not types: 3 meetings + 2 list versions + 4 testing rounds = 9 files. Task PDF page 3 explicitly prefers fewer stages that genuinely hold over stages done as theater, and a defended cut over a hollow one.

### Types considered and cut, with reasons
- **Email thread — CUT.** What it contributed ("a request that arrived outside the written list") is already contributed by meeting notes; two types filling one column means one is redundant. Also removes any suggestion of email-system integration, which was never intended — an email thread would only ever be a `.txt` file someone saved into the watched folder. If a real email file does appear in an evaluator's pile, the three-bucket handling catches it as bucket 2 (`related, unrecognised type`), so nothing breaks.
- **Internal feature spec — CUT.** Originally framed as a document that *decides* what to build. No such document existed at Arka — the written list arrived and the whole list got built. Inventing it would have been the exact thing that collapses under questioning.
- **Status update / delivery note — CUT.** Considered as the source for a *Built?* column, but delivery happened once as a whole handover, not as per-feature progress updates. Testing feedback already proves existence: a customer can only test what exists. The *Built?* column was therefore removed rather than backed by an invented document.

### The rule that resolves what belongs in the register
**The register records FACTS, not JUDGEMENTS.**

| Column asks | Column never asks |
|---|---|
| What was requested? | Should it have been requested? |
| Is it in writing? | Should it have been? |
| What did testing find? | Was the customer right? |

Every column is "what happened," never "what should have happened." Judgements belong to the human at review time — which is exactly what task PDF page 2 requires: the system surfaces the conflict, it does not resolve it.

### Blockers — a status, not a document type
At Arka, an incoming request was checked for blockers; if one existed, the team went back to the customer (usually via a fresh meeting) and the feature waited until it cleared, then shipped end to end.

A blocker is a **state a request sits in**, not a document. Its record lives in meeting notes, which is already a declared type. So it adds no new type — it adds one register column and one status value.

`Blocked` is a distinct problem from `Disputed`:
- **Disputed** = two documents say different things.
- **Blocked** = work is stopped, waiting on someone's answer.

Blockers earn their column because they surface a finding nothing else can: *a request blocked weeks ago, the answer never came, and nobody followed up.*

## Register — final shape (LOCKED 2026-08-09)

**Columns:** Request · First appeared · In writing? · Blocker · What testing found · Status
**Status values:** Delivered · Disputed · Blocked · Not built

Every cell carries a source citation (`filename, section`). Conflicts attach to their row.

### Worked example — the declared domain end to end

Source pile:

**`meeting-notes-mar12.md`**
> Client discussed the intake form. They want an email to go out to the applicant after submission.

**`feature-request-v2.md`**
> 1. Intake form with validation
> 2. Save submissions to database
> 3. SMS alerts on status change

*(no mention of email — that stayed verbal)*

**`meeting-notes-mar20.md`**
> Asked client for SMS gateway credentials before we can build SMS alerts. Awaiting response.

**`testing-feedback-mar28.md`**
> Form works. But no email is being received by applicants. This is a bug.

Resulting register:

| Request | First appeared | In writing? | Blocker | What testing found | Status |
|---|---|---|---|---|---|
| Intake form | `feature-request-v2.md` | ✅ | — | Works | Delivered |
| DB save | `feature-request-v2.md` | ✅ | — | No issues | Delivered |
| Email notification | `meeting-notes-mar12.md` | ❌ | — | "not being received" | **Disputed** |
| SMS alerts | `feature-request-v2.md` | ✅ | Gateway credentials requested from client (`meeting-notes-mar20.md`), no response | — | **Blocked** |

**Row 3 is the point of the whole system.** The customer calls it a bug; the written record says it was never requested. The system states both and resolves neither — the human decides.

**Row 4 is the second kind of finding.** Nothing is in conflict; work is simply stopped and forgotten. Only the blocker column surfaces it.

**Worked example — an incremental update on the register above:** later, `meeting-notes-apr15.md` arrives — the customer supplied the SMS gateway credentials, and separately confirmed the email notification was in fact agreed verbally and should be treated as in-scope. The system must touch only two rows: the SMS alerts row (`Blocked` → unblocked) and the email notification row (its conflict now has new evidence). The intake-form and DB-save rows must remain byte-identical, and the system must be able to prove that. Neither change commits without human approval.

## Request identity — how one row is formed (LOCKED 2026-08-09, v1 starting point)

> **Status: v1 starting point, deliberately revisitable.** Locked so the build has a defined place to start. Expect real findings once we run this on an actual pile — revise here, and record what changed and why.

**The problem.** The same request appears across several documents in different wording:

| Document | Wording |
|---|---|
| `meeting-notes-mar12.md` | "They want an email to go out to the applicant after submission" |
| `feature-request-v2.md` | "Email notification on form submit" |
| `testing-feedback-mar28.md` | "no email is being received by applicants" |

A human sees one request. Without a matching rule the system produces three rows instead of one — and then the conflict is never detected, because the competing claims sit in separate rows.

The mirror danger matters just as much: *"email notification"* and *"SMS notification"* are close in wording but are **different** requests. Wrongly merging is as damaging as wrongly splitting.

**Locked method:** when a new candidate request is extracted, the current register is passed to the model, which decides: match an existing row, or create a new one. **No embedding/vector layer in this path.**

- **Match** → no new row; the source citation is *added* to the existing row. One row accumulates several citations, which is how *First appeared* and *What testing found* both get filled on a single row.
- **Uncertain** → do not merge and do not guess. Flag the row (`possibly the same as row N`) and let the human decide at review. This is behaviour #5 (never bluff) applied to row identity.
- **Wrong merges are recoverable** — the human gate sits in front of the register, so a bad merge cannot pass silently.

**Why no embeddings — rejected, do not resurface.** An embedding shortlist was considered (retrieve nearest rows, then let the model judge only those) and rejected:
- The register is tiny — ~15 rows × ~15 words ≈ 250 tokens. There is nothing to narrow down; the whole register fits in one call.
- It introduces a **new failure mode that does not otherwise exist**: if the shortlist misses the correct row, the model never sees it and the mismatch happens silently. We would be adding a place to break, for no gain.
- It adds an embedding dependency, a vector table, and a similarity threshold to tune.

Also rejected: **ticket-ID matching** (Arka had no ticket IDs — building on something that did not exist), and **exact text matching** (real documents never repeat wording).

**Note on pgvector.** Task PDF page 3 recommends PostgreSQL with vector search for retrieval. Row matching is not that job. Vector retrieval's real use would be pulling relevant passages out of long source documents — but our declared document types are short and will likely be read whole. **Open:** if we finish the build without needing vector retrieval, say so explicitly in the write-up as a defended decision rather than quietly dropping a recommended stack component.

## Request granularity — how big is one row (LOCKED 2026-08-09, v1 starting point)

> **Status: v1 starting point.** Same as request identity — locked to give the build a defined place to start, expected to be revisited once we run on a real pile.

**The problem.** A written list item may bundle several things: `1. Intake form with validation` — one request, or two?

Both extremes hurt:
- **Too coarse** → a conflict hides inside a row. "The form works but validation is broken" has nowhere to live.
- **Too fine** → 50 noisy rows, harder matching, an unreadable register.

**Locked rule:**

> Granularity comes from the **source document**, not from us. Whatever the customer wrote as one item is one row.

- `1. Intake form with validation` → **one** row
- `1. Intake form  2. Validation` → **two** rows

**Why this rule and not our own judgement.** It follows directly from the already-locked principle that the register records facts, not judgements. Splitting a customer's single line into two rows is *us* deciding how the work decomposes — that decision is not a fact present in any document. Taking the customer's own cut keeps every row traceable to something actually written.

**Sub-part problems still surface.** If testing shows part of a bundled row failing, that lands in the *What testing found* column rather than forcing a new row:

| Request | In writing? | What testing found | Status |
|---|---|---|---|
| Intake form with validation | ✅ | Form submits fine; validation not catching empty fields | **Disputed** |

Nothing is hidden and nothing is invented.

**Defence line if asked why this is one row:** "Because the customer wrote it as one item. Re-cutting their list would be my judgement, not theirs — the register only reports what was written and what happened to it."

**Parked for later (not building now):** if a customer bundles many distinct asks into a single bullet, the system could **flag** the row (`this row appears to bundle several asks`) without splitting it, leaving the split to the human at review. Deliberately deferred — the simple rule ships first. Revisit once we see how real bundling behaves on an actual pile.

## Run scope — one run is one project (LOCKED 2026-08-09)

**The question.** Does a pile handed to a run contain one customer's project, or possibly several?

**Why it matters:**
1. **Register scope** — two projects in one pile means one table holding rows from two unrelated worlds.
2. **Matching breaks** — Client A's "intake form" and Client B's "intake form" would wrongly merge into one row.
3. **Behaviour #9** — task PDF page 3 requires that "two runs at the same time stay two runs, whether they are two piles or the same pile hit twice," so a run needs a stable identity.

**Locked:** one run's pile = the documents of **one project**. This follows the task PDF's own framing on page 2 ("takes in **related** documents"), and matches how the work actually ran at Arka — each customer's documents were their own set, never mixed.

**How the system knows which project it is on.** The run is started with a project identifier alongside the folder:

```
start_run(project = "Acme intake portal", folder = "./piles/acme")
```

This gives every downstream decision a reference to compare against, and it is machine-drivable, which is what behaviour #4 requires — the same call is exposed as an MCP tool.

**Out-of-project documents are already handled.** A document that is not about the named project falls into **bucket 3** (`unrelated → skip with reason`), which was locked earlier. The project identifier is what makes that decision defensible rather than vague:

> `beta-crm-notes.md` skipped — not about the Acme intake portal; describes a different system.

**Connection to the open concurrency risk.** The previously flagged same-pile-twice risk now has a concrete key: if a run is started twice for the same project identifier, the system must detect it and either refuse or isolate. The idempotency guarantee attaches to the **project identifier**. Still to be designed and tested.

---

## Rules and playbook (LOCKED 2026-08-09)

**What a rule is.** One line stating what should have been true. The system reads that line, checks the documents against it, and where it is broken, raises a finding.

**Rules come from the user, not from us.** Task PDF page 2: *"The user hands it the rules they care about."* So rules live in a **config file**, never inside code — task PDF page 12 requires that a new rule be *"a data change, not a rewrite."*

**Default file, not hardcoding.** The repo ships a filled-in `rules.yaml` so a fresh clone actually runs — behaviour #6 requires a stranger to reach a working system in minutes, and a system that demands a rule file it does not provide fails that. The evaluator can edit it or point at their own file; the code does not change either way. README must state this explicitly.

```yaml
rules:
  - id: R1
    text: "Anything built must have a written request. A verbal mention in a meeting is not enough."

  - id: R3
    text: "No request should stay blocked without follow-up."
    params:
      max_days: 14
```

The `max_days` parameter is the clearest demonstration of configuration-over-code: changing the threshold is editing a number, not touching logic.

**The four locked rules** — each one is a failure Aditya actually lived at Arka, which is what makes them defensible:

| ID | Rule | What it catches |
|---|---|---|
| **R1** | Anything built must have a written request; a verbal mention is not enough | The email-notification case — requested in a meeting, never in any written list |
| **R2** | Testing feedback asking for new behaviour is a change request, not a bug | Customer calls it a bug; the written record shows it was never requested |
| **R3** | No request stays blocked beyond `max_days` without follow-up | The SMS-alerts case — credentials requested, no reply, nobody followed up |
| **R4** | Every written request must have a testing outcome | Work that quietly fell through and was never verified |

**Why only four.** Task PDF page 3 prefers fewer things that genuinely hold over more done as theater. Ten rules are easy to write and hard to demonstrate working; four can each be proven.

**Rules do not violate the facts-not-judgements principle.** The register records facts only. Findings are judgements — but they are the *user's* judgements, encoded in the rules they supplied, and every finding is still gated by human approval before it commits. The system never invents a standard of its own.

### Finding record shape (LOCKED 2026-08-09)

Five fields, all required:

```
Finding F-03
Rule:      R1 — a written request is required
Found:     Email notification entered scope discussion but appears in no written request list
Evidence:  meeting-notes-mar12.md, "Discussion"    → requested verbally
           feature-request-v2.md                    → absent
           testing-feedback-mar28.md, "Issues"      → customer calls it a bug
Row:       #3 Email notification
Decision:  Treat as a change request, or accept as agreed scope?
```

- **Evidence** is the field that satisfies task PDF page 2 — *"each pointing to the exact place it came from."* A finding without an exact source location is not shippable.
- **Decision** is what keeps the human gate real: the system states the problem and asks; it never resolves the finding itself.
- Findings carry a review state (`pending` / `approved` / `rejected`) so mixed decisions in one review session work, and rejecting one finding leaves the others untouched — task PDF page 2, behaviour #3.

### Deliverable-side rules (LOCKED 2026-08-09)

Task PDF page 2 requires checking the sources **and the deliverable**. Two rules run against the register itself:

- **D1** — every row carries at least one source citation
- **D2** — no row is marked `Delivered` without a testing outcome

**Why these exist:** R1–R4 catch problems in the *documents*. D1–D2 catch problems in the *system's own output* — a row built without evidence, or a status asserted without backing. This is behaviour #5 (never bluff) turned inward on ourselves.

### The `No findings` path (LOCKED 2026-08-09)

When nothing is broken, the system reports exactly that. Two rules:

- **Never manufacture a finding.** A weak or invented finding to look thorough is a failure, not a save. Task PDF page 2 calls an honest report of no findings *"the rarest output in this industry"* — the empty result is itself the signal of quality.
- **An empty result must not look like a crash.** Output states what actually ran: *"4 rules evaluated across 9 documents — no findings."* A blank screen reads as a failed run and breaks behaviour #5's requirement that a success message only ever means the output is genuinely in the state it claims.

---

## Repository layout (LOCKED 2026-08-09)

**Decision.** One line governs the whole tree: **what is needed to run the
system lives at the root; what is background reading lives under
`documentation/`.** A stranger should understand the repo from the root listing
alone — that is behaviour #6 turned into a folder structure.

```
/
├── README.md · TASK.md · DECISIONS.md · PROGRESS.md
├── pyproject.toml · docker-compose.yml · .env.example
│
├── app/              the system — ingest/ register/ rules/ api/ mcp/
├── ui/               the React review screen
├── tests/
├── migrations/       Alembic
├── config/           rules.yaml — everything changeable without touching code
├── sample-piles/     synthetic corpora: the demo pile and the second-run pile
│
└── documentation/    background; not needed to run anything
    ├── superdocs-engineering-task/   the task PDF, the working notes,
    │                                 the review protocol
    ├── product-research/
    ├── testing-intel/
    ├── reference/
    └── product-test-files/           docx/pdf files produced while
                                      probing SuperDocs
```

**Three renames made on the way here, each fixing a name that would have misled
someone later:**

- `documentation/task2-engineering/` → `documentation/superdocs-engineering-task/`.
  The folder holds the brief for Tasks 1 through 4; the "2" meant Round 2, not
  Task 2, and every reader would have got that wrong. The task PDF only bars
  "SuperDocs" from the *repository* name, so a folder may carry it.
- `documentation/test-docs/` → `documentation/product-test-files/`. Once
  `tests/` exists, two unrelated things would have been called "test" — one
  holds Word and PDF files from probing SuperDocs, the other holds our test
  suite. "artifacts" was considered and rejected: in software that word means
  build output, which is not what these are.
- `sample-piles/` promoted to the root. It is not documentation; it is the data
  the run command points at, so a stranger has to find it immediately.

**Folders inside `app/` are named after the work, not the file type** —
`ingest/`, `register/`, `rules/`. No `helpers/`, no `utils.py`; those always
become the drawer everything gets thrown into.

**Trade-off.** `app/` and `ui/` and `tests/` are created empty (with
`.gitkeep`) before any code exists. Slightly premature, accepted deliberately:
settling the shape while the repo holds four files is far cheaper than moving
forty later.

**Note.** Task 2's build does not live here — it goes as a pull request to the
public `superdocsapp/superdocs-builds` repository. This repository is Task 1.

---

## Review interface — scope (LOCKED 2026-08-09)

**Decision.** One page, four sections. Not a dashboard product, and not a
two-button list either — an earlier sketch of "a list and two buttons" was too
small, because two graded behaviours land on this screen and not only the
approval one.

```
┌─────────────────────────────────────────┐
│  Run: Acme intake portal                │
│                                         │
│  STAGES        ← behaviour #1           │
│  ✓ ingest      9 files, 1 skipped  1.2s │
│  ✓ classify    3 types found       4.1s │
│  ✓ extract     12 requests         8.7s │
│  ⏸ review      waiting for you          │
│                                         │
│  SKIPPED       ← bucket 2 / bucket 3    │
│  beta-crm-notes.md — not this project   │
│                                         │
│  REGISTER      ← behaviour #3   [✓] [✗] │
│  Intake form      Delivered             │
│  Email notif      Disputed  ▸           │
│    ├ meeting-mar12: asked verbally      │
│    └ request-v2:    absent              │
│                                         │
│  Run cost: ₹4.20 · 21.3s  ← behaviour #10│
└─────────────────────────────────────────┘
```

**Why each section is there, in the brief's words:**

- **Stages** — behaviour #1: *"the system moves through visible stages and shows
  what it decided at each one."* Watchability is graded; it has to be visible
  somewhere, and this is the somewhere.
- **Skipped** — the three-bucket handling only counts if the reason is
  surfaced. "Skipped" alone is not honest; "skipped, and here is why" is.
- **Register** — behaviour #3: item-by-item approve and reject, and rejecting
  one item must not disturb the others.
- **Cost and timing** — behaviour #10: *"what it spent and where the time went,
  stage by stage."*

**Deliberately out of scope:** no sidebar, no settings page, no charts, no
design system, no state library. `useState` and `fetch` for one screen.

**Where creativity belongs here.** Not in decoration — the brief never asks for
a good-looking interface, and page 3 prefers *"fewer stages that genuinely
hold"* over theater. The creative decisions are about **what gets shown**: both
sides of a conflict next to each other so a human can decide without opening a
file; the *reason* a file was skipped rather than the fact of it; how long a
blocked request has been stuck. That is judgement, not styling.

**Beyond the brief, marked optional.** The working notes say a human can
"approve, reject, modify, or resolve" a finding. The brief itself (page 2) only
requires **approve and reject**. Modify and resolve are our own addition — build
them only if the required behaviours are all finished and time remains.

---

## Build order — vertical slices (LOCKED 2026-08-09)

**Decision.** Build in thin end-to-end slices, riskiest property first, user
interface last. Each slice closes one graded behaviour and leaves something that
actually runs.

**Alternatives rejected:**

- **Boilerplate first** — scaffold FastAPI, React, the database and the graph
  with dummy data, then fill in logic. Rejected because every graded behaviour
  here is a *runtime* property — resume, concurrency, the gate, machine-drive —
  and none of them can be exercised on a scaffold holding fake data. The
  approach reliably discovers the hardest problems last, when the least time is
  left.
- **Full paper design first** — rejected because checkpoint granularity cannot
  honestly be designed without watching a real checkpointer behave. The design
  would be wrong in exactly the details that matter.

**Slice 1 — the narrowest thing that proves the riskiest property:**

one `.md` file in → the graph runs → two rows in the register → `interrupt()`
→ approve over the API → export. Then kill the process mid-run and start it
again: it must continue without redoing finished work or duplicating a row.

No interface, no rules engine, no MCP, no PDF or DOCX — only `.md`, and approval
over `curl`. If this survives a kill, the most dangerous part of the build is
already proven.

**Then widen, one behaviour per slice:** remaining formats and bucket handling →
rules engine and findings → MCP wrappers over the same API → incremental update
with its invariance proof → concurrency and idempotency → the review interface →
cost and timing.

**Why the interface is last.** Behaviour #4 requires approval to be an API
operation, so the API *is* the real interface and the screen is a thin client
over it. Building the screen first would mean rebuilding it once the register's
real shape is known.

**Trade-off, stated honestly:** leaving the interface until late risks it being
rushed. Accepted because it is genuinely one screen and the API behind it will
already be proven by then — but if the schedule slips, this is the first place
the damage will show.
