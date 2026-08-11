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

The **Decision Log is append-only**. When a decision changes, keep its original
row, mark it `SUPERSEDED <date> by <replacement>`, and add the replacement as a
new dated row. Detailed sections below are different: they are the canonical
current spec and must not retain a conflicting old section.

**Nothing here is a claim of evidence.** Where an entry says the reasoning is
untested, it is untested — those must be upgraded to real evidence before the
write-up repeats them.

---


## Decision Log
| Date | Decision | Reason | Trade-off | Proof / Link | Follow-up |
|---|---|---|---|---|---|
| 2026-08-09 | Agent orchestration = **LangGraph** (raw `StateGraph` for Task 1); LangChain only as thin `langchain-core` layer; no legacy chains/`AgentExecutor` | Brief behaviours #1, #2, #3, #9 are LangGraph built-ins; it is the founder's own named stack, so zero deviation cost; checkpointer shares our existing PostgreSQL | More boilerplate than a hand-rolled loop; real learning curve; still leaves ~5.5 of 10 behaviours for us to build | Research-stage only — see "Orchestration framework decision" section | Convert to real evidence via resume test, same-pile concurrency test, and stage-timing numbers before write-up |
| 2026-08-09 | Task 2 orchestration shape (`create_agent` vs `StateGraph`) **deferred** | `create_agent` runs on the LangGraph runtime, so deciding later is not a rewrite; Task 1 is the current focus | Task 2 stack stays formally open a while longer | — | Decide when Task 2 starts, against the SuperDocs four-call contract |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by the reviewed register decision:** Task 1 deliverable = register/table (initial proposal) | Stable rows appeared best for focused updates and exact unchanged proof | The choice had not yet been compared carefully with a brief and report | Reasoning-stage only | Reopened, compared, and replaced by the 2026-08-11 decision below |
| 2026-08-11 | Task 1 deliverable = **Requirements-to-Delivery Register**; one row traces one client requirement | Stable row units make focused updates, exact unchanged proof, item-level review, citations, and machine use simpler than narrative prose | Rows can compress nuance; detailed evidence/history must remain available outside the summary cells | Reasoning-stage; risks reviewed against a worked example | Design columns and prove row-level invariance on sample piles |
| 2026-08-09 | Accepted formats = **`.pdf`, `.docx`, `.md`, `.txt`** (hardcoded gate) | These are the shapes real project documents arrive in; `.eml` parsing adds cost with no evaluation gain | Images and spreadsheets excluded | — | Declare the list in README (task PDF page 4) |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by primary / related additional / unrelated:** unrecognised types = known / related-unknown / unrelated | Avoided both strict filename/type filtering and unrestricted processing | `related-unknown` was unclear and sounded unsupported | Reasoning-stage only | Reframed with explicit guarantees in the next decision |
| 2026-08-11 | Document-type handling = **primary / related additional / unrelated**, decided from content at runtime | A strict type list would discard useful delivery evidence, while processing unrelated files would contaminate the analysis | Related additional types receive best-effort handling rather than a type-specific guarantee | Reasoning-stage | Second-run test must include one related additional and one unrelated file |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by Software Requirements-to-Delivery:** domain = Software feature delivery; actors = customer and development team | Captured the original feature request → build → testing loop | Too narrow at feature level and actor names did not cover freelancers, agencies, or other providers cleanly | Reasoning-stage only | Replaced after first-principles domain review |
| 2026-08-11 | Domain = **Software Requirements-to-Delivery**; actors = **Client** and **Software Provider** | Generalises the requirements → clarification → build/configure → client testing → feedback loop Aditya lived without narrowing the system to one company, product, or feature type | Deliberately excludes pre-sales and full project/commercial management | Current domain contract below; build evidence still needed | Validate with two different synthetic client engagements |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by the current primary types:** meeting notes, feature request list, testing feedback | Each type supplied a distinct part of the proposed register | `feature request list` was narrower than the real written-requirements input | Reasoning-stage only | Replaced by the current primary document types below |
| 2026-08-11 | Primary document types = **3** (meeting notes, client requirements document, testing feedback); related additional documents are also processed | These are the minimum sources needed for discussion, written scope, and client validation; a delivery summary may add evidence but is not required | Extra related types get best-effort handling rather than a type-specific guarantee | Reasoning-stage | Prove with one related additional document and one unrelated document |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by blocker as a domain condition:** blocker = register status plus column | A blocked requirement needed to be visible in the original register proposal | It prematurely fixed representation before register fields were designed | Reasoning-stage only | Representation deferred to register-field design |
| 2026-08-11 | Blocker = a **domain condition**, not a document type; final output representation deferred | A blocker exists when work is explicitly stopped by a missing answer or dependency, regardless of which related document reports it | Column/status design remains open until the deliverable is chosen | Reasoning-stage | Revisit during deliverable design |
| 2026-08-11 | Target user and human reviewer = one provider-side **Delivery Owner** | One accountable role keeps V1 aligned with the real small-team workflow; the client supplies requirements and clarification evidence but does not operate the system | No client login, shared approval, or multi-role permissions in V1 | Reasoning-stage | Define the exact human-gate actions separately |
| 2026-08-09 | Request identity = **model matches candidate against the whole register; no embedding layer**. Uncertain → flag, never merge | Register is ~250 tokens, so nothing needs narrowing; an embedding shortlist would add a silent-miss failure mode for no gain | Cost grows with register size — fine at this scale, revisit if a pile ever produces hundreds of rows | v1 starting point, no build evidence yet | Re-examine after the first real run; if vector retrieval ends up unused anywhere, defend that in the write-up |
| 2026-08-09 | Request granularity = **the source document's own cut**; one written item = one row | Re-cutting the client's list would be our judgement, not a fact in any document — violates the locked facts-not-judgements rule | A bundled bullet becomes one broad row | v1 starting point | Bundle-detection flag is parked, not built; revisit after the first real pile |
| 2026-08-09 | **SUPERSEDED 2026-08-11 by document-batch processing cycle:** one run = one project | Kept unrelated project documents out of one register | Conflated the continuing project context with an individual execution and made legitimate updates ambiguous | Reasoning-stage only | Project and run are separated in the next decision |
| 2026-08-11 | **One run = one complete processing cycle for one submitted document batch** | Separates a durable project/register from each initial or later update execution | Every run belongs to one project context; unrelated projects cannot be mixed | Reasoning-stage | Define run identity, idempotency, and concurrency separately |
| 2026-08-09 | **Review interface scope** — one page, four sections (stages · skipped · register · cost) | Behaviours #1 and #10 land on this screen too, not just #3; an earlier "list and two buttons" sketch was too small | More UI than planned, though still one screen | — | `modify`/`resolve` are beyond the brief — optional only |
| 2026-08-09 | **Build order = vertical slices**, riskiest property first, interface last | Every graded behaviour is a runtime property and cannot be exercised on a dummy-data scaffold | Interface risks being rushed at the end | — | Slice 1 must prove kill-and-resume before anything widens |
| 2026-08-09 | **Repository layout** — runnable things at the root, background under `documentation/`; three folders renamed | A stranger must understand the tree from the root listing alone (behaviour #6); the old names would have misled readers | Empty `app/`/`ui/`/`tests/` exist before any code | — | Fill them as code arrives |
| 2026-08-09 | Rules live in a user-supplied **`rules.yaml`**, with a filled-in default shipped in the repo; **4 rules locked** (R1–R4) | Task PDF page 2 says the user hands over the rules; page 12 requires a new rule to be a data change; a default file is needed for behaviour #6 (fresh clone runs) | Four rules cover less ground than a long list, but each can actually be demonstrated | — | Prove rule-file swapping in the demo |
| 2026-08-09 | Finding = **5 required fields** (rule, found, evidence, row, decision) + review state | Evidence field satisfies the exact-source requirement; decision field keeps the human gate real; review state enables mixed approve/reject in one session | Rigid shape; a finding that fits none of the fields has nowhere to go | — | Watch for findings that resist the shape during build |
| 2026-08-09 | **D1/D2 deliverable-side rules** — every row cites a source; no `Delivered` without a testing outcome | Task PDF page 2 requires checking the deliverable too; these catch the system's own bad output, not just bad documents | Two extra checks per run | — | Must be covered by tests |
| 2026-08-09 | `No findings` is a **first-class output** — never manufacture, never render as a blank/crash | Task PDF page 2 calls an honest no-findings report the rarest output; behaviour #5 requires success messages to be true | — | — | Needs a test asserting a clean corpus yields zero findings and a non-empty message |
| 2026-08-09 | PDF extraction = **pdfplumber** (primary) + **pypdf** (encryption check only); scanned and encrypted PDFs skipped with reason | pdfplumber preserves table structure; pypdf adds one-line `.is_encrypted`; two libraries, two jobs, zero overlap | 300 KB extra dependency (pypdf); no scanned PDF support | Tested on 7 PDFs including 59-page IRS doc (14 tables, 315K chars) and 22-page MSA — zero data loss across all pages | Add OCR only if domain expands to scanned documents |
| 2026-08-10 | **Classify step dropped** — LLM infers document type during extraction; no separate classification node | Heuristics fragile on real documents; LLM context window naturally discerns meeting notes vs feature lists vs testing feedback; extra node adds complexity with no value | Six nodes instead of seven; simpler graph | — | — |
| 2026-08-11 | Human-gate scope = **13 scenarios**, gated wherever the system judges or changes an existing row | Keeps the gate scarce so the two genuinely dangerous items are not lost among mechanical ticks on plain facts | On a first run most rows are plain, so the gate is thin — mostly findings plus the final export | Reasoning-stage only — see "Human-gate scope" section | Define the reject action — what happens once something is rejected |
| 2026-08-11 | Human-gate actions = **Approve / Reject only**, identical at all seven gated points; buttons act on a stated proposal, not an object | Task PDF page 2: human "approves what is right and rejects what is wrong ... item by item"; per-object verbs (solve/park/merge) would be seven separate failure modes | No custom per-scenario actions; on a conflict the buttons decide only whether it is shown, never which side is right | Reasoning-stage — see "Human-gate actions" section | README owes the reject-limitation note (see next row) |
| 2026-08-11 | Reject = **excluded from the register, kept permanently in the run record**; final, not conditional | Makes "do not ask again" possible — without a permanent record the same finding returns on every later run | A rejected finding that later becomes *stronger* through new evidence stays suppressed in V1 | Reasoning-stage — see "Human-gate actions" section | Document as an honest README limitation |
| 2026-08-11 | Incremental input contract — **a batch is every new and changed file waiting when a run starts**; a later file is its own run; the Delivery Owner or a machine starts the run | Conflicts live between files, not inside one; task PDF's own "an update should cost like an update"; one review sitting instead of three | Trigger is a v1 starting point, not the PDF's own rule — auto-start risks the same-pile-twice problem behaviour #9 grades | Reasoning-stage — see "Incremental input contract" section | README owes the run-trigger assumption note; revisit trigger at architecture phase |
| 2026-08-11 | Register shape = **seven columns**, per-cell citations, three kinds of attachment (conflicts, findings, possible-match flag) | Per-cell citation follows the brief directly; attachments stay off the row to preserve the human-gate lock and the unchanged-rows proof | Supersedes the six-column NOT LOCKED proposal and its worked example, which used the old status set | Reasoning-stage — see "Register shape" section | — |
| 2026-08-11 | Status values = **five** (`Done` · `Partial` · `Never happened` · `Blocked` · `Disputed`), provisional, config-changeable | `Blocked` and `Never happened` are different problems to the Delivery Owner; a status column earns its place once a register is too long to scan as plain text | Deliberately provisional — more values may be added later; adding one must be a config edit, never code | Reasoning-stage — see "Register shape" section | — |
| 2026-08-11 | Citations = **file + place + quoted words**; each format supplies the locator it can actually produce | A filename alone is not "the exact place" the brief asks for; quoted words mean the Delivery Owner usually never opens the source file | Rejected one uniform locator across formats — a line number is a poor locator inside a PDF | Reasoning-stage — see "Citations" section | Quote-length maximum lives in config |
| 2026-08-11 | Export = **JSON as the record, Markdown generated from it** | JSON is what machines read (behaviour #4) and what the unchanged-proof compares; Markdown is for the Delivery Owner to read and send on | One source of truth only — Markdown is never edited directly | Reasoning-stage — see "Export, audit history, and unchanged proof" section | — |
| 2026-08-11 | Audit history at **cell level**; unchanged proof by a **per-row fingerprint over cells only**, attachments excluded | Cell-level audit answers all three of the brief's questions (what/when/which source); excluding attachments stops one new finding marking an unmoved requirement "changed" | Two instruments kept deliberately separate rather than merged into one | Reasoning-stage — see "Export, audit history, and unchanged proof" section | — |
| 2026-08-11 | Everything the system produces is in **English** — register, statuses, findings, logs, exports, and repository documentation | Keeps the deliverable and codebase in one language regardless of what language design conversations happen in | — | Reasoning-stage — see "Register shape" section | — |
| 2026-08-11 | D2 amended: no row marked **`Done`** (not `Delivered`) without a testing outcome | `Delivered` no longer exists once the five-value status set locked; D2 must track the current status set | — | Reasoning-stage — see "Deliverable-side rules" section | Closes the "D2 depends on an unlocked status" audit item |
| 2026-08-11 | Phase 1's three open items — brief acceptance contract, behaviours 6–10 coverage, React/FastAPI/MCP boundary — **deferred to build time**, not cut | Writing pass/fail checks or a component boundary before the relevant design exists would be guesswork; task PDF page 8's order (never-do → test → code) still holds | Phase 1 counted complete with these three items open | Reasoning-stage | Each item resolved just before its own build slice; a later cut must carry its reason into the Task 4 write-up |

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

## Deliverable shape — Requirements-to-Delivery Register (LOCKED 2026-08-11)

- **Decision:** Task 1's grounded deliverable is a **Requirements-to-Delivery Register** — one row traces one client requirement — not a narrative brief or report.
- **Problem:** The brief offers three shapes ("a register, a brief, or a report", Task PDF page 2) and we must pick one before designing state, extraction, or the review UI.
- **Alternatives:** narrative brief, narrative report. Both explicitly permitted by the brief.
- **Reason:** Driven by the brief's *incremental update* requirement (page 2) — when a new document arrives, unaffected output must stay **exactly** as it was and the system must be able to **prove** it. A row is a natural unit of change: new document → 2 rows change, the rest stay byte-identical, provable by row-level hash comparison. Narrative prose has no such unit — an LLM rewrite perturbs wording in untouched paragraphs, making invariance almost impossible to prove.
- **Trade-off:** Summary cells carry less nuance than prose. Each row therefore keeps expandable evidence, history, testing details, and attached findings; the register remains the core deliverable.
- **Evidence:** Reasoning-stage. Must be proven by an actual incremental-update test showing unaffected rows unchanged.
- **Limitation:** If a finding genuinely does not fit a row shape, it will be forced into the conflicts section rather than the table. Watch for this during build.
- **Next improvement:** Revisit only if the row model actually breaks in practice; do not pre-optimise.

**Output flow:** documents → system builds register → human review → approved register exported.

The deliverable type and one-requirement-per-row mental model are locked. Exact
columns, statuses, row-matching behaviour, review actions, UI presentation,
storage, and export format remain open for their own decision blocks.

## Domain — Software Requirements-to-Delivery (LOCKED 2026-08-11)

**Declared domain (this exact line goes in the README):**

> **Software Requirements-to-Delivery** — the documents created after a client
> starts sharing software requirements, while a software provider clarifies,
> builds or configures and delivers the work, and while the client tests it and
> returns feedback or changes.

### Actors

- **Client:** the person or organisation that provides the software
  requirements and validates the delivered result.
- **Software Provider:** the freelancer, team, agency, or software company that
  clarifies the requirements and builds, configures, or fixes the software.

### Workflow boundary

The domain starts when actual client requirements begin to be discussed or
collected. A call containing only a product introduction, demo, pricing, or deal
discussion is pre-sales and outside the domain. If that same call records an
actual software requirement, that requirement is inside the domain.

The tracked workflow is:

`requirement discussion → written requirements → clarification/blockers → build
or configuration → client testing → feedback/change/fix loop`

The Task 1 system observes this workflow through documents. It does not build,
configure, deploy, or fix the software itself, and it never assumes delivery or
success without source evidence.

### Domain conditions already agreed

- **Documentation gap:** a requirement appears in meeting notes but not in the
  client requirements document. Surface the gap for a human decision; absence
  alone is not a conflict.
- **Conflict:** two sources make incompatible claims about the same
  requirement. Surface both; never choose one silently.
- **Blocker:** work is explicitly stopped by a missing answer or dependency.
  A missing detail alone is not a blocker unless a source says work is stopped.
- **New or updated information:** no existing semantic match means a new
  requirement; compatible detail enriches the existing requirement;
  incompatible meaning uses the conflict path.
- **Testing feedback:** classify each feedback item as `Passed`, `Defect`,
  `Change request`, or `Unclear`. Testing information may appear in meeting
  notes or another related document, not only in a file labelled testing
  feedback.
- **Baseline correctness:** crashes, silent data loss, failed core actions, and
  false-success behaviour are defects even when a client did not spell out
  basic failure handling. A request for additional behaviour beyond the agreed
  requirement is a change request. If evidence cannot distinguish the two,
  report `Unclear` for human review.

### Out of scope

Pre-sales material, product demos, pricing, contracts, SOWs, invoices, payments,
source-code execution, deployment work, sprint/resource management, and CRM
integration are not part of this document-analysis domain.

## Target user and human reviewer (LOCKED 2026-08-11)

- **Delivery Owner:** the person on the Software Provider side who owns the
  client requirements-to-delivery workflow. A freelancer, founder, project
  lead, or engineer may fill this one role.
- The Delivery Owner operates the system and performs its mandatory human
  review. These are two actions by the same person, not two V1 user roles.
- The client supplies requirements, testing feedback, and clarifications but
  does not log in to or approve inside the V1 system. Client decisions enter as
  new source evidence.
- Which objects are gated for approve/reject is decided — see "Human-gate
  scope" below. The gate's two actions, and what reject means, are decided too
  — see "Human-gate actions" below.

## Human-gate scope (LOCKED 2026-08-11)

**The rule that generates the table:** the gate applies where the system is
making a **judgement** or **changing something that already exists**. Where it
is only copying a fact, it does not.

| # | Scenario | Gate? | Reason |
|---|---|---|---|
| 1 | A new row, entirely fresh — no conflict, no uncertainty | No | The system copied a fact with its citation; no judgement was applied |
| 2 | New evidence added to an existing row, same meaning | No | Same fact, more proof; nothing changed |
| 3 | A new document changes the meaning of an existing row | Yes | This is a conflict; the system may not decide it |
| 4 | Possible match to an existing row — the system is unsure | Yes | A wrong merge corrupts the register silently and is hard to catch later |
| 5 | Conflict — two sources make incompatible claims | Yes | The brief's own rule: surface both sides, the human chooses |
| 6 | Rule finding (R1–R4) | Yes | A judgement, drawn from the user's own supplied rules |
| 7 | Deliverable-side finding (D1/D2) | Yes | The system doubting its own output; it must not clear itself |
| 8 | Blocker — work is explicitly stopped | No | A fact written in a source document, not an opinion |
| 9 | Suspicious instruction found inside a source document | No | Reported only; the system already refused to follow it, so approve/reject has no meaning |
| 10 | A file was skipped, with its reason | No | Information, not a proposed action; a wrong skip is re-run, not rejected |
| 11 | An update run's focused change proposal | Yes | The brief requires it explicitly; existing output is being changed |
| 12 | Final export / commit | Yes | The hard floor — nothing leaves the system without it |
| 13 | A `No findings` report | No | No action was proposed |

**Why the gate stays scarce.** Scenario 12 (final export) already gates the
whole register, so plain rows are never released without approval —
item-by-item ticking is not required for facts. A 12-row first run needing 12
ticks would bury the two genuinely dangerous items in mechanical noise.

**The feared case is already covered.** "Requested verbally in a meeting,
absent from the written requirements document" is not a plain row — it
produces a row *and* an R1 finding, and the finding is gated (scenario 6). No
separate rule is needed.

**Alternatives rejected:** (a) gate on every register row — rejected for the
attention-dilution reason above; (b) gate only on the final export — rejected
because conflicts, findings, and updates are named individually in the brief
(task PDF page 2) and must be decidable item by item.

**Status.** Reasoning-stage; no build evidence yet. On a first run most rows
are plain, so the gate is thin — mostly findings plus the final export. That is
correct behaviour, not a weakness — do not write this up as proven.

The reject action — what happens once a finding or proposal is rejected — is
decided next, in "Human-gate actions" immediately below.

## Human-gate actions (LOCKED 2026-08-11)

**Two buttons only: Approve / Reject.** Identical at all seven gated points —
no per-object verbs (no solve, park, merge).

**The buttons act on a stated proposal, not on an object.** At every gated
point the system states what it intends to do; Approve makes it happen,
Reject stops it. Task PDF page 2: *"a person reviews what the system intends
to do, approves what is right and rejects what is wrong ... item by item, and
the system respects every decision."*

**What each button means, scenario by scenario:**

| # | Scenario | System proposes | Approve | Reject |
|---|---|---|---|---|
| 3 | New document changes an existing row's meaning | "Attach this opposing claim to row #4, both sides" | Both claims show on the row | Row stays as it was |
| 4 | Uncertain match | "Merge this new request into row #7?" | One row | Two separate rows |
| 5 | Conflict | "Show this conflict on row #3, both sides" | Conflict shows in the register | It does not |
| 6 | Rule finding | "R1 broken — attach this finding to row #3" | Finding travels with the row | It does not |
| 7 | Deliverable finding | "D1 broken — this row carries no source citation" | Finding shows | It does not |
| 11 | Update proposal | "Change these 2 rows, leave the other 6 untouched" | Change applies | Register unchanged |
| 12 | Final export | "Export this register" | Export happens | It does not |

**On a conflict, the buttons only decide whether the conflict is shown** —
never which side is right. Choosing a side would be resolving it, which the
brief forbids.

**Reject = excluded from the register, kept in the run record, permanently.**
The record is what makes "do not ask again" possible; without it the same
finding returns on every later run. Reject is final, not conditional.

**Alternatives rejected:** per-object custom actions (solve/park/merge) —
theatre, and seven separate failure modes instead of one; conditional reject
(reopens when new evidence arrives) — over-engineering.

**Honest limitation for the README.** A rejected finding that later becomes
*stronger* through new evidence stays suppressed in V1. The common case — new
evidence that *resolves* the problem — is safe, because the rule simply stops
breaking and no finding is produced at all.

**Not the audit-trail requirement.** The task PDF's audit-trail line ("what
changed, when, and because of which source") is about the register's own
changes, not about keeping rejected findings. Keeping them is our own choice,
made for the repeat-suppression reason above — the PDF is not the source for
it.

## One-run scope (LOCKED 2026-08-11)

- A **project context** owns one continuing Requirements-to-Delivery Register.
- A **run** is one complete processing cycle for one submitted document batch.
- The initial document pile creates the first run. Each later batch, such as an
  updated document, new requirements, or testing feedback, creates another run
  against the same project register.
- One run cannot mix documents from unrelated project contexts.
- Each run will have its own identity, status, timing, cost, and recoverable
  execution state. Exact identity and duplicate-run behaviour remain open for
  the architecture decision.

## Incremental input contract (LOCKED 2026-08-11)

**One run consumes every new file waiting at the time it starts** — not one
run per file. A later file, or a new version of an existing document, becomes
its own run against the same project register.

**Reason for batching rather than one-run-per-file:** conflicts live *between*
files, not inside one; the task PDF's own standard is that "an update should
cost like an update"; and it gives the Delivery Owner one review to sit
through instead of three.

> **Trigger — v1 starting point, deliberately revisitable.** Locked so the
> build has a defined place to start. May be reopened during the architecture
> phase, exactly like request identity.

The system watches the location and reports what has arrived; the run itself
is started by the Delivery Owner, or by a machine through the same operation.
Auto-start was rejected: it would break the one-run-one-batch lock, and is the
easiest route into the "same pile hit twice" duplicate-run problem behaviour
#9 grades. Behaviour #4 is unaffected either way — the trigger is an
operation a machine can call.

**Product-level promise:** the system detects arrivals itself; the Delivery
Owner never has to announce a new file. *How* it detects, and where the
watched location is configured, is architecture-phase work (`PROGRESS.md`,
"Define watched-folder and focused-update architecture").

The task PDF does not say who starts a run. This is a logged assumption under
the PDF's own page-4 rule — make a reasonable call, write it and the reasoning
down. It belongs in the README, not only here.

**A batch holds both new and changed files; only the changed part of an
edited file is processed, never the whole document again.** This half is the
brief's own requirement — task PDF page 2: "not a rewrite and not a full
re-run ... an update should cost like an update." Working out what changed
inside an edited file means the system must retain the earlier version —
architecture-phase work, same Phase 3 box.

**A file removed from the watched location changes nothing.** Its rows stay
in the register. The document did arrive once; deleting the file does not
make that untrue.

## Declared set — file formats and document types (LOCKED 2026-08-09)

Terminology, kept separate on purpose (conflating these caused real confusion once):
- **File format** = can the file be opened? (`.pdf`, `.docx`, `.md`, `.txt`) — a parsing question.
- **Document type** = what is inside it? (meeting notes, client requirements document, testing feedback) — a meaning question.

Every incoming file passes two checks, in order: **format first, then type.** A format failure stops before the type check ever runs.

### Lock 2a — accepted file formats
- **Accepted:** `.pdf`, `.docx`, `.md`, `.txt`. Anything else is skipped with reason `unsupported format`.
- **Reason:** these are the shapes real project documents actually arrive in. Email threads are represented as `.txt`/`.md` files rather than `.eml`, avoiding mail-parsing complexity for no evaluation gain.
- **Trade-off:** images/screenshots and spreadsheets are out. Acceptable — task PDF page 8 rails spreadsheet-output products out anyway, and screenshots carry no extractable claim text.
- **This list is deliberately hardcoded.** Task PDF page 12 permits this: intentional hard-coded defences alongside intelligent logic are a legitimate fix, not a patch. Intelligence belongs in the type decision, not the format gate.
- **README must declare this list** — task PDF page 4 requires the accepted formats and domains to be stated, because a second run means different documents inside the declared set.
- **PDF extraction:** `pdfplumber` (text + table extraction) with `pypdf` for encryption detection only. Scanned PDFs and encrypted PDFs are skipped with a message naming the reason and the fix. Full decision and evidence in the PDF library choice section below.
- **DOCX extraction:** `python-docx` — standard library, extracts paragraphs and table cells. No alternatives needed.
- **MD and TXT:** No library required — Python's built-in `open().read()`. Plain text, no extraction complexity.
- **Encoding:** UTF-8 assumed with Latin-1 fallback. If both fail, file skipped with reason `unreadable encoding`.
- **Folder scan:** Top-level files only. Subfolders ignored. Documents read in-place — no copy, no upload.
- **Pre-processing:** None. pdfplumber and python-docx produce clean output. Text passed raw to next node.
- **Processing order:** Sequential, one document per node pass. Extraction is fast (~1s for 9 documents); parallelism adds complexity with no meaningful speed gain. Kill-resume covers every document boundary via the checkpointer.

### Lock 2b — primary, related additional, and unrelated documents
When a file opens successfully, the system decides — it is not matched against a hardcoded filename list:

| Bucket | Condition | Action |
|---|---|---|
| 1. Known type | Matches one of the declared document types | Process fully |
| 2. Related additional type | Belongs to this client software engagement, but is not one of the three primary types | Extract relevant facts and identify it as a `related additional document` |
| 3. Unrelated | Not about this client software engagement at all (e.g. a resume) | Skip, with the reason recorded |

- **Alternatives rejected:** (A) strict — process only the declared types, skip everything else. Rejected: a hardcoded type list is exactly the "fixed script with labels" the task PDF warns against on page 2. (B) open — attempt to process anything. Rejected: irrelevant files would contaminate the analysis.
- **Reason for the middle path:** the classification decision is made by the system at runtime, satisfying task PDF page 12 ("intelligence in the system deciding, code executing"), while the format gate stays deterministic.
- **Evidence:** must be proven by a second-run test using a different pile that deliberately contains one bucket-2 and one bucket-3 file.

---

## Document types — the declared list (LOCKED 2026-08-11)

Three primary document types receive the declared behaviour guarantee:

| # | Document type | What it may contain |
|---|---|---|
| 1 | **Meeting Notes** | Requirement discussions, clarifications, blockers, delivery statements, or testing comments |
| 2 | **Client Requirements Document** | The client's written software requirements and later compatible additions |
| 3 | **Testing Feedback** | Passed checks, defects, change requests, and unclear testing observations |

Facts are classified from content, not from filenames alone. Testing evidence,
for example, may appear in meeting notes. A related delivery summary, email
export, or other supported-format document is processed as a related additional
document; the system does not require or depend on a formal delivery summary.

The three primary types keep the guaranteed path small and testable. A second
run must also prove one related additional document is used and one unrelated
document is skipped with a reason.

### Output principle — facts, not judgements
**The grounded deliverable records facts, not judgements.**

| Output may report | Output must not decide |
|---|---|
| What was requested? | Should it have been requested? |
| Is it in writing? | Should it have been? |
| What did testing find? | Was the client right? |

Every output field asks "what happened," never "what should have happened."
Judgements belong to the human at review time — the system surfaces a conflict
but does not resolve it.

### Blockers — a domain condition, not a document type
When a requirement cannot proceed because the Software Provider needs an answer
or dependency, the blocker may be reported in meeting notes or any other
related document.

A blocker is a **condition a requirement sits in**, not a document type. Its
final representation stays open until register fields and statuses are decided.

A blocker is distinct from a conflict:
- **Conflict** = two documents make incompatible claims.
- **Blocker** = work is explicitly stopped, waiting on an answer or dependency.

## Register shape (LOCKED 2026-08-11)

This replaces the earlier not-locked column/status proposal below it in
history. Worked example carried through this section and the two that follow:

`meeting-notes-10-mar.md` records a call asking for a notification on form
submit, **WhatsApp** as well, and **search over old records**.
`client-requirements-v1.md` writes down only the form with validation, an
**email** notification, and a records list page — no WhatsApp, no search.
`testing-feedback-25-mar.md` reports the form and email working, and the list
page opening but **missing search — "this is essential"**. A later
`meeting-notes-20-mar.md` records that WhatsApp is waiting on API credentials
the client has not sent.

### Columns — seven

`What was asked` · `In writing?` · `What testing found` · `Status` ·
`Blocked on` · `First seen` · `Last moved`

**Every cell carries its own citation, not one per row.** Two cells on one row
routinely come from two different documents. Task PDF page 2: "every claim in
the deliverable traces to the exact place in the sources it came from."

**`Blocked on` is its own column** — `Status` holds one word; the reason plus
its citation will not fit inside it.

**Two dates, and why both are needed.** Without them rule R3 cannot run at
all — "blocked longer than `max_days`" is unanswerable if nothing records when
the block started, and three days stuck looks identical to three months
stuck. Dates come from the document, not from the run: a 20 March meeting
note delivered on 10 April describes 20 March, and the run date only records
when the system happened to look — the two give opposite R3 answers on the
same row. When no date can be found, the cell says "date unknown" and R3
simply does not run on that row (behaviour #5: say what is not supported
rather than invent it).

**"In writing? = No" carries its own evidence**, not the bare word "No" — for
example "`client-requirements-v1.md` read in full, no mention of search."
This is where R1 fires and where the client argument actually happens, so an
unsupported "No" is the most expensive wrong cell in the register. An absence
is a claim too, and the per-claim citation rule covers it.

**Testing observations carry a label:** `Passed` · `Defect` · `Change
request` · `Unclear`. Rule R2 ("testing feedback asking for new behaviour is
a change request, not a bug") cannot run without it. In the worked example
above, the list page opening without search is a real defect; search itself
was never in writing, so asking for it is a change request — the client calls
both a bug. Where the evidence cannot separate the two, the label is
`Unclear` and the system does not decide.

### Status — five values, provisional

`Done` · `Partial` · `Never happened` · `Blocked` · `Disputed`

Deliberately provisional: more may be added once the product is being built.
Adding one is a config edit, never a code change (task PDF page 12, "a data
change, not a rewrite"). `Blocked` and `Never happened` are kept deliberately
separate: one is a wait with a known cause, the other is something that fell
through silently — entirely different problems to the Delivery Owner. A
status column earns its place once a register is too long to scan as plain
text.

### Conflicts, findings, and the possible-match flag attach to a row — they are not columns

Four reasons, the last two load-bearing:

1. One row can carry several; a column holds one.
2. A finding has its own internal shape (rule, what was found, evidence, the
   question for the human) that will not fit in a cell.
3. **It would break the human-gate lock.** Plain rows are not gated but
   findings are; a finding living inside the row would let approving the row
   silently approve the finding too.
4. **It would break the unchanged-rows proof.** A finding stored inside the
   row changes the row's content the moment a new finding lands — marking it
   changed when the client's requirement never moved.

The "possibly the same as row N" flag attaches the same way, for the same
reasons — it is a question for the human, not a property of the requirement.

**Everything the system produces is in English.** The register, its status
values, findings, logs, exports, and all repository documentation are
English. Hinglish is only how Aditya and Claude talk while deciding — it
never reaches a file, a cell, or a screen.

## Citations (LOCKED 2026-08-11)

**Three parts: file · place · the words themselves.** For example:
`meeting-notes-10-mar.md` · page 2, "Discussion" · *"they also want search
over old records."* A filename alone is not "the exact place" the brief asks
for — on a 20-page PDF it sends the reader off to hunt. Carrying the quoted
words means the Delivery Owner usually never has to open the file at all.

**Each format supplies the location it can actually produce:**

| Format | Location |
|---|---|
| `.pdf` | page number (pdfplumber reads page by page) |
| `.md` | nearest heading |
| `.docx` | nearest heading — Word stores no page numbers; where a page breaks is decided at render time, and `python-docx` returns paragraphs. Claiming "page 4" from a `.docx` would be inventing it. |
| `.txt` | line number |

**Rejected: forcing one uniform locator across all four formats.** A line
number is a poor locator inside a PDF, where the page is what a reader can
actually use.

**Quote length:** roughly one sentence — enough for the claim to stand on its
own. A maximum length lives in config (a client who writes paragraph-long
bullets should not inflate the register), changed by editing config, never
code.

## Export, audit history, and unchanged proof (LOCKED 2026-08-11)

### Export — JSON and Markdown

JSON is the real record: machines read it directly (behaviour #4), and it is
what the unchanged-proof compares. Markdown is generated from it for the
Delivery Owner to read and send on. One register, two surfaces — no second
source of truth.

### Audit history — cell level

Each entry: **which cell · what it was · what it is now · which run · which
source document.** Tested against the brief's own three questions ("what
changed, when, and because of which source"), row-level history answers only
two — "row 4 changed" points at a row without saying what moved, leaving the
Delivery Owner to hunt for it. Cell-level history answers all three, at no
extra cost — it is the same data.

Attachments arriving or leaving are recorded here too: "finding F-02 attached
to row 5, run 2, `meeting-notes-20-mar.md`."

### Unchanged proof — one fingerprint per row, over the cells only

Not per column, not per cell, and **attachments are excluded**.

- Fingerprint unchanged → that row's requirement did not move by a single
  byte. This is the brief's proof ("byte-identical where you promise
  untouched").
- Fingerprint changed → audit history says exactly which cell moved.

**Why attachments are excluded:** run 2 attaching a new finding to row 5
without touching any of its cells must leave row 5 counted as **unchanged**,
because the brief's claim is about the client's requirement, and that
requirement did not move. The finding is not lost — audit history records
it. Including attachments in the fingerprint would mark every affected row
"changed" while no requirement had moved, making the unchanged-rows claim
look false when it is not.

**Two separate questions, two separate instruments, deliberately not
merged:**
- "Did this requirement change at all?" → the fingerprint
- "What else happened on this row?" → audit history

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

> Granularity comes from the **source document**, not from us. Whatever the client wrote as one item is one row.

- `1. Intake form with validation` → **one** row
- `1. Intake form  2. Validation` → **two** rows

**Why this rule and not our own judgement.** It follows directly from the already-locked principle that the register records facts, not judgements. Splitting a client's single line into two rows is *us* deciding how the work decomposes — that decision is not a fact present in any document. Taking the client's own cut keeps every row traceable to something actually written.

**Sub-part problems still surface.** If testing shows part of a bundled row failing, that lands in the *What testing found* column rather than forcing a new row:

| Request | In writing? | What testing found | Status |
|---|---|---|---|
| Intake form with validation | ✅ | Form submits fine; validation not catching empty fields | **Disputed** |

Nothing is hidden and nothing is invented.

**Defence line if asked why this is one row:** "Because the client wrote it as one item. Re-cutting their list would be my judgement, not theirs — the register only reports what was written and what happened to it."

**Parked for later (not building now):** if a client bundles many distinct asks into a single bullet, the system could **flag** the row (`this row appears to bundle several asks`) without splitting it, leaving the split to the human at review. Deliberately deferred — the simple rule ships first. Revisit once we see how real bundling behaves on an actual pile.

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
| **R2** | Testing feedback asking for new behaviour is a change request, not a bug | Client calls it a bug; the written record shows it was never requested |
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
           testing-feedback-mar28.md, "Issues"      → client calls it a bug
Row:       #3 Email notification
Decision:  Treat as a change request, or accept as agreed scope?
```

- **Evidence** is the field that satisfies task PDF page 2 — *"each pointing to the exact place it came from."* A finding without an exact source location is not shippable.
- **Decision** is what keeps the human gate real: the system states the problem and asks; it never resolves the finding itself.
- Findings carry a review state (`pending` / `approved` / `rejected`) so mixed decisions in one review session work, and rejecting one finding leaves the others untouched — task PDF page 2, behaviour #3.

### Deliverable-side rules (LOCKED 2026-08-09)

Task PDF page 2 requires checking the sources **and the deliverable**. Two rules run against the register itself:

- **D1** — every row carries at least one source citation
- **D2** — no row is marked `Done` without a testing outcome

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
