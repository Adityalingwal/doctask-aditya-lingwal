# SuperDocs Round 2 — Working Notes

## Technology Stack (All Tasks)
- **Backend:** Python + FastAPI
- **Agent orchestration:** **LangGraph (LOCKED 2026-08-09)** — full rationale in "Orchestration framework decision" below. Brief-permitted alternatives (LangChain-only, AutoGen, CrewAI, hand-rolled loop) evaluated and rejected there.
- **Database:** PostgreSQL + pgvector (vector search for retrieval; also hosts the LangGraph checkpointer — one DB, not two)
- **Review interface:** React
- **Machine interface:** MCP server (strongest version of behavior 4; founder's own stack)
- Source: Task PDF, page 3 "The Stack." Stack deviation allowed with reasoning documented in write-up. No deviation taken — LangGraph is explicitly named in the brief.

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

## Product Familiarization — Before Building
- Build start karne se pehle SuperDocs account bana kar product ko hands-on use karna hai.
- Safe own/public/synthetic document par complete workflow verify karna hai: upload → targeted instruction → review proposed edits → approve → export.
- Product behaviour, confusing UX, latency, failures, aur reproducible bugs ko record karna hai; useful bugs promptly report karne hain.
- Official docs (`docs.superdocs.app`) read karni hain before API integration.
- API workflow/constraints ko hands-on verify karna hai; task build API side par depend karega.
- Coding agent use ho to official agent-signup flow evaluate karna hai; agent-created account bhi candidate ki responsibility hai.
- **⚠️ Before building:** check SuperDocs features page + docs thoroughly. Candidates often build around gaps that don't exist: review mode, version history/revert, live progress, citation preservation, and agent self-signup are already shipped. See "Final FAQ clarifications" for full list.

## Build & Founder Discussion Readiness

### Goal
- Yeh task poori technical evaluation hai.
- Strong submission ke baad founder ke saath direct discussion hogi.
- Discussion mein build ko saath dekhna aur live modify karna ho sakta hai.
- Isliye build aisa hona chahiye jise main independently explain, run, debug aur safely modify kar sakun.

### Evaluation priorities
- Founder explicitly evaluates: creativity, agency, grit, aur technical ability.
- Creativity aur grit ko raw technical ability se zyada weight diya gaya hai.
- Isliye sirf technically correct build enough nahi hai: useful original thinking, independent execution, aur blockers ke through persist karna visible hona chahiye.
- Practical response to a blocker: scope intelligently decide karo, workable alternative ship karo, evidence do, aur limitation/next step honestly record karo.

### For every important decision, record
- **Decision:** Kya choose kiya?
- **Problem:** Isse kaunsi problem solve ho rahi hai?
- **Alternatives:** Aur kya options the?
- **Reason:** Yeh option kyun choose kiya?
- **Trade-off:** Is choice se kya mila aur kya compromise hua?
- **Evidence:** Test, screenshot, logs, measurement, ya demo proof kya hai?
- **Limitation:** Yeh choice kin cases mein weak/fail ho sakti hai?
- **Next improvement:** Time milne par isko kaise better karunga?

### System understanding checklist
- User se input aane se final output/export tak end-to-end flow samajhna hai.
- Har external dependency/API/model ka role aur failure behaviour samajhna hai.
- Data kahan store hota hai, state kaise track hoti hai, aur resume/retry kaise hota hai — yeh clear hona chahiye.
- Main happy path ke saath failure paths bhi explain kar sakun.
- Har important feature ko demo ke bina bhi verbally explain kar sakun.

### Live modification readiness
- Demo se pehle project locally run hona chahiye.
- README mein exact setup/run/test commands verified hon.
- Seed/sample data available ho, taaki live demo reproduce ho sake.
- Important config `.env.example` mein ho; real keys kabhi commit ya screen par nahi.
- Small, safe changes jaldi karne layak code structure ho.
- Known issues aur risky areas pehle se documented hon.
- Agar live change fail ho, to cause diagnose karke fallback/next step explain kar sakun.

### Honesty rule
- Jo kaam nahi karta, usko working claim nahi karna.
- Unsupported claim ya missing evidence ko clearly flag karna.
- Known limitation batana weakness nahi; limitation ko detect aur explain kar pana strength hai.
- AI tools se code bana ho, tab bhi architecture, logic, tests aur limitations meri understanding mein hone chahiye.

### Ongoing decision log
- Har non-obvious decision ko build ke time turant log karna hai.
- Format: `date | decision | reason | trade-off | proof/link | follow-up`.
- Yeh log README, write-up, demo script aur founder discussion ke source material ke roop mein use hoga.

## Notes-file rules
- Notes should separate confirmed brief requirements from planning assumptions or implementation ideas.
- Any assumption must be labeled clearly as an assumption/hypothesis, not as a brief requirement.
- Use synthetic/public/shareable data only throughout examples, demos, tests, and screenshots.
- Preserve founder-recommended defaults first; document deviations only with explicit rationale.
- Prefer honest gaps/limitations over inflated claims.
- When a section is covered, keep one compact checklist so future sanity checks can quickly verify completeness.

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
| 2026-08-09 | Rules live in a user-supplied **`rules.yaml`**, with a filled-in default shipped in the repo; **4 rules locked** (R1–R4) | Task PDF page 2 says the user hands over the rules; page 12 requires a new rule to be a data change; a default file is needed for behaviour #6 (fresh clone runs) | Four rules cover less ground than a long list, but each can actually be demonstrated | — | Prove rule-file swapping in the demo |
| 2026-08-09 | Finding = **5 required fields** (rule, found, evidence, row, decision) + review state | Evidence field satisfies the exact-source requirement; decision field keeps the human gate real; review state enables mixed approve/reject in one session | Rigid shape; a finding that fits none of the fields has nowhere to go | — | Watch for findings that resist the shape during build |
| 2026-08-09 | **D1/D2 deliverable-side rules** — every row cites a source; no `Delivered` without a testing outcome | Task PDF page 2 requires checking the deliverable too; these catch the system's own bad output, not just bad documents | Two extra checks per run | — | Must be covered by tests |
| 2026-08-09 | `No findings` is a **first-class output** — never manufacture, never render as a blank/crash | Task PDF page 2 calls an honest no-findings report the rarest output; behaviour #5 requires success messages to be true | — | — | Needs a test asserting a clean corpus yields zero findings and a non-empty message |

## Task 1 — Shared Agentic System

### Task framing
- Yeh round ka common engineering task hai; isi brief par candidates ko directly compare kiya jayega.
- Scope intentionally small-team-level hai; expectation hai ki one person + AI high-leverage execution dikhaye.
- Task ko “too big” karke avoid nahi karna; intelligent scoping ke saath real agentic system behaviour dikhana hai.

### Domain and source-data rule
- Aisa document domain choose karna hai jise confidently explain aur defend kar sakun.
- System related documents ke pile par kaam karega, jahan documents same reality describe karte hue contradict kar sakte hain.
- Repository/demo ke liye sirf synthetic, public, ya legally shareable own documents use karne hain.
- Confidential employer/client/NDA data ya third-party private documents kabhi use/commit/upload nahi karne hain.

### Core system outcome
- Multi-document AI analyst system banana hai: documents ingest kare, type/context identify kare, facts extract kare, contradictions aur material gaps/rule violations identify kare, aur source-backed final report/brief/register banaye.
- Har material claim/finding ke saath exact evidence location deni hai: filename + page/section/paragraph/text span as applicable.
- System conflict ko silently resolve ya overwrite nahi karega; competing claims aur evidence human ke saamne surface karega.
- Human har finding ko approve, reject, modify, ya resolve kar sake; same review session mein mixed decisions support hone chahiye, aur rejected item ko change karne par unrelated approved findings preserve rehne chahiye.

### Deliverable shape — register/table (LOCKED 2026-08-09)

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

### Domain — Software feature delivery (LOCKED 2026-08-09)

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

### Declared set — file formats and document types (LOCKED 2026-08-09)

Terminology, kept separate on purpose (conflating these caused real confusion once):
- **File format** = can the file be opened? (`.pdf`, `.docx`, `.md`, `.txt`) — a parsing question.
- **Document type** = what is inside it? (meeting notes, feature request, testing feedback) — a meaning question.

Every incoming file passes two checks, in order: **format first, then type.** A format failure stops before the type check ever runs.

#### Lock 2a — accepted file formats
- **Accepted:** `.pdf`, `.docx`, `.md`, `.txt`. Anything else is skipped with reason `unsupported format`.
- **Reason:** these are the shapes real project documents actually arrive in. Email threads are represented as `.txt`/`.md` files rather than `.eml`, avoiding mail-parsing complexity for no evaluation gain.
- **Trade-off:** images/screenshots and spreadsheets are out. Acceptable — task PDF page 8 rails spreadsheet-output products out anyway, and screenshots carry no extractable claim text.
- **This list is deliberately hardcoded.** Task PDF page 12 permits this: intentional hard-coded defences alongside intelligent logic are a legitimate fix, not a patch. Intelligence belongs in the type decision, not the format gate.
- **README must declare this list** — task PDF page 4 requires the accepted formats and domains to be stated, because a second run means different documents inside the declared set.

#### Lock 2b — unrecognised document types (three-bucket handling)
When a file opens successfully, the system decides — it is not matched against a hardcoded filename list:

| Bucket | Condition | Action |
|---|---|---|
| 1. Known type | Matches one of the declared document types | Process fully |
| 2. Related, unknown type | Belongs to this project, but is a type we did not declare | Extract facts, flag as `unrecognised document type` |
| 3. Unrelated | Not about this project at all (e.g. a resume) | Skip, with the reason recorded |

- **Alternatives rejected:** (A) strict — process only the declared types, skip everything else. Rejected: a hardcoded type list is exactly the "fixed script with labels" the task PDF warns against on page 2. (B) open — attempt to process anything. Rejected: irrelevant files would pollute the register.
- **Reason for the middle path:** the classification decision is made by the system at runtime, satisfying task PDF page 12 ("intelligence in the system deciding, code executing"), while the format gate stays deterministic.
- **Evidence:** must be proven by a second-run test using a different pile that deliberately contains one bucket-2 and one bucket-3 file.
- **Open:** the declared document-type list itself is not locked yet (see the superseded product-team example below).

### Agentic behaviour and observable steps
- Demo-specific hardcoded pipeline nahi banana; real input variability ke against system robust hona chahiye.
- **Second-run reliability:** system sirf demo document set ke saath nahi, declared domain/formats ke andar kisi bhi different document set ke saath chalna chahiye. Founder explicitly evaluates this — "a second run means different documents inside that declared set."
- Unsupported formats (outside declared set) ko gracefully skip karna hai with reason, crash nahi karna.
- Workflow visible, inspectable steps mein chale: e.g. ingest → classify → extract → compare/examine → generate findings/update proposal → human review → commit/export.
- Har step ka current state, output, aur important decision/reason observable hona chahiye, taaki run ko watch/debug/review kiya ja sake.
- Stage output/observations ke basis par next action/path change ho sake; system static linear script nahi hona chahiye.
- System ko messy/variable documents, missing fields, irrelevant files, duplicate facts, conflicting evidence, parse failures, aur incomplete evidence handle karna hai.
- Example decision paths: parse fail → retry/fallback parser/human escalation; irrelevant file → skip with reason; insufficient evidence → unsupported/needs-review finding; conflict → human review queue; unclear rule → clarification/escalation.
- Sirf single LLM call + UI, ya fixed script stages ko labels dena, sufficient agentic behaviour nahi hoga.

### Stop-resume reliability
- Run ke beech process kill/stop ho jaaye to restart par system ko jahan chhoda tha wahan se continue karna chahiye.
- Already finished work lose nahi hona chahiye aur unnecessary full rerun/reprocessing avoid hona chahiye.
- Intermediate state/progress/checkpoints durable form mein save hone chahiye, taaki resume deterministic aur auditable ho.
- Resume ke baad duplicate findings, duplicate commits, ya repeated side effects nahi hone chahiye.

### Machine-drivable interface
- Workflow sirf manual UI clicks par dependent nahi hona chahiye; machine/script/agent bhi run drive kar sake.
- Documents ingest/start run, progress/status fetch, findings/conflicts/updates read, aur human approval/rejection decisions machine interface se submit kiye ja sake.
- Human gate mandatory rahega, lekin approval action API/tool-call compatible hona chahiye; browser-only hidden action nahi hona chahiye.
- Isse automation, testing, replay, and agent-to-agent orchestration possible honi chahiye.

### Reproducibility for a stranger
- Fresh clone ke baad ek unfamiliar technical evaluator/developer minutes mein documented command(s) se system run kar sake.
- README mein verified prerequisites, setup steps, `.env.example`, seed/sample data, exact run command, test command, aur expected first successful outcome hona chahiye.
- **README must clearly declare** which document formats (.pdf, .docx, .txt, etc.) and which domain(s) the system accepts — so a second run with different documents inside that declared set also works.
- Instructions creator ke private machine state, unstated manual setup, local secrets, ya tribal knowledge par depend nahi honi chahiye.
- Final submission se pehle clean/fresh environment ya equivalent independent run se setup verify karna hai.

### Automated proof via tests
- System ke meaningful automated tests hone chahiye, aur core test suite live paid API key ke bina runnable honi chahiye.
- Tests real behaviour verify karen; sirf trivial mocks ya static assertions enough nahi.
- At minimum, tests ko important guarantees cover karni chahiye: stop/kill ke baad resume, concurrent runs/state safety, aur malicious document instructions ke against resistance.
- Test command documented aur reproducible hona chahiye; evaluator ko quickly confidence milna chahiye ki key claims actually prove kiye gaye hain.

### Prompt-injection resistance
- Uploaded documents ke andar likhe instructions/commands ko system executable authority ki tarah treat nahi karega; unhe document content/data ki tarah handle karega.
- Document text jaise `ignore instructions`, `approve everything`, `export now`, ya tool-call-like strings ko follow nahi karna; zarurat pade to suspicious instruction/content ke roop mein flag karna.
- System prompts, tool authority, human approval gate, aur machine interface controls document content se override nahi hone chahiye.
- Is behaviour ko tests/examples ke through prove karna hai.

### Concurrent-run safety
- Ek hi time par multiple runs aane par unki state, checkpoints, findings, review decisions, aur side effects isolate rehne chahiye; silent cross-run corruption nahi honi chahiye.
- Different document piles ke runs ek doosre ka data mix na karein.
- Same pile par accidental duplicate/concurrent run aaye to system safely isolate, deduplicate, queue, ya explicit conflict strategy se handle kare.
- Is guarantee ko tests ke through prove karna hai.

### Cost and timing visibility
- Har run ke liye total duration aur estimated model/API cost visible honi chahiye.
- Stage-by-stage timing breakdown dena chahiye, for example ingest/parse, classification, extraction, analysis, aur report generation.
- Breakdown observability aur bottleneck detection ke liye useful hona chahiye; sirf single total time kaafi nahi hai.
- Isko submission docs mein explicit operational behavior ke roop mein mention karna chahiye.

### No-bluff reliability
- System unsupported claim ko supported jaisa present nahi karega; insufficient evidence ho to clearly `unsupported`, `insufficient evidence`, ya equivalent honest status dikhayega.
- Guess, silent fill-in, fake certainty, ya fabricated citations/links/locations allowed nahi.
- Success state tabhi show karni hai jab underlying operation actually complete hui ho: e.g. export successful sirf real export ke baad, commit/update successful sirf durable commit ke baad.
- User-visible status/messages reality-synced hone chahiye; optimistic message without actual durable result avoid karna hai.

### Rule-based examination
- User system ko applicable rules de sakta hai: compliance checklist, contract playbook, policy, style guide, ya custom business rules.
- System ko input document pile **aur generated final deliverable** dono ko supplied rules ke against examine karna hai.
- Rule violation/missing evidence/failure milne par finding banani hai: exact rule, relevant source evidence, why it may violate/fail the rule, confidence/uncertainty where relevant, aur required human decision.
- Rule uncertain ho, evidence incomplete ho, ya high-impact action ho to system khud se final decision/commit nahi karega; human review/approval gate use karega.
- Koi issue na mile to honestly `No findings found` report karna hai; fake or weak finding bana kar impressive dikhne ki koshish nahi karni.

#### Rules and playbook (LOCKED 2026-08-09 — rules + config shape; finding shape still open)

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

#### Finding record shape (LOCKED 2026-08-09)

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

#### Deliverable-side rules (LOCKED 2026-08-09)

Task PDF page 2 requires checking the sources **and the deliverable**. Two rules run against the register itself:

- **D1** — every row carries at least one source citation
- **D2** — no row is marked `Delivered` without a testing outcome

**Why these exist:** R1–R4 catch problems in the *documents*. D1–D2 catch problems in the *system's own output* — a row built without evidence, or a status asserted without backing. This is behaviour #5 (never bluff) turned inward on ourselves.

#### The `No findings` path (LOCKED 2026-08-09)

When nothing is broken, the system reports exactly that. Two rules:

- **Never manufacture a finding.** A weak or invented finding to look thorough is a failure, not a save. Task PDF page 2 calls an honest report of no findings *"the rarest output in this industry"* — the empty result is itself the signal of quality.
- **An empty result must not look like a crash.** Output states what actually ran: *"4 rules evaluated across 9 documents — no findings."* A blank screen reads as a failed run and breaks behaviour #5's requirement that a success message only ever means the output is genuinely in the state it claims.

### Document types — the declared list (LOCKED 2026-08-09)

Three types. Each one feeds a **different** register column — that is the test a type must pass to earn its place. Two types filling the same column would mean one is redundant.

| # | Document type | What is inside | Register column it feeds |
|---|---|---|---|
| 1 | **Meeting notes** | What was discussed with the customer; what they said verbally | *First appeared* — and specifically the case where a request exists **only** verbally |
| 2 | **Feature request list** | The customer's written list of what to build | *Request* itself + *In writing? ✅* |
| 3 | **Testing feedback** | What the customer reported after testing | *What testing found* |

**Three types is not thin.** A pile is made of files, not types: 3 meetings + 2 list versions + 4 testing rounds = 9 files. Task PDF page 3 explicitly prefers fewer stages that genuinely hold over stages done as theater, and a defended cut over a hollow one.

#### Types considered and cut, with reasons
- **Email thread — CUT.** What it contributed ("a request that arrived outside the written list") is already contributed by meeting notes; two types filling one column means one is redundant. Also removes any suggestion of email-system integration, which was never intended — an email thread would only ever be a `.txt` file someone saved into the watched folder. If a real email file does appear in an evaluator's pile, the three-bucket handling catches it as bucket 2 (`related, unrecognised type`), so nothing breaks.
- **Internal feature spec — CUT.** Originally framed as a document that *decides* what to build. No such document existed at Arka — the written list arrived and the whole list got built. Inventing it would have been the exact thing that collapses under questioning.
- **Status update / delivery note — CUT.** Considered as the source for a *Built?* column, but delivery happened once as a whole handover, not as per-feature progress updates. Testing feedback already proves existence: a customer can only test what exists. The *Built?* column was therefore removed rather than backed by an invented document.

#### The rule that resolves what belongs in the register
**The register records FACTS, not JUDGEMENTS.**

| Column asks | Column never asks |
|---|---|
| What was requested? | Should it have been requested? |
| Is it in writing? | Should it have been? |
| What did testing find? | Was the customer right? |

Every column is "what happened," never "what should have happened." Judgements belong to the human at review time — which is exactly what task PDF page 2 requires: the system surfaces the conflict, it does not resolve it.

#### Blockers — a status, not a document type
At Arka, an incoming request was checked for blockers; if one existed, the team went back to the customer (usually via a fresh meeting) and the feature waited until it cleared, then shipped end to end.

A blocker is a **state a request sits in**, not a document. Its record lives in meeting notes, which is already a declared type. So it adds no new type — it adds one register column and one status value.

`Blocked` is a distinct problem from `Disputed`:
- **Disputed** = two documents say different things.
- **Blocked** = work is stopped, waiting on someone's answer.

Blockers earn their column because they surface a finding nothing else can: *a request blocked weeks ago, the answer never came, and nobody followed up.*

### Register — final shape (LOCKED 2026-08-09)

**Columns:** Request · First appeared · In writing? · Blocker · What testing found · Status
**Status values:** Delivered · Disputed · Blocked · Not built

Every cell carries a source citation (`filename, section`). Conflicts attach to their row.

#### Worked example — the declared domain end to end

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

### Request identity — how one row is formed (LOCKED 2026-08-09, v1 starting point)

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

### Request granularity — how big is one row (LOCKED 2026-08-09, v1 starting point)

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

### Run scope — one run is one project (LOCKED 2026-08-09)

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




### Incremental updates and auditability
- System one-time analyzer nahi hai; new documents/case updates aane par report ko alive rakhna hai.
- Watched location/folder ya chosen intake mechanism se new file detect/ingest karna hai.
- Sirf new file aur usse affected facts/findings ko process karna hai; full re-analysis/rewrite default nahi hona chahiye.
- Focused update proposal banana hai. Unaffected report sections exactly unchanged rehne chahiye, aur system ko is invariance ka proof dena chahiye.
- New source existing claim/finding ko contradict kare to conflict surface karna hai; silently overwrite/decide nahi karna.
- Human approval ke bina update commit/export nahi hoga.
- Audit trail answer de sake: kya badla, kab badla, aur kis source document/evidence ki wajah se badla.

**Worked example (continues the register example above):** later, `meeting-notes-apr15.md` arrives — the customer supplied the SMS gateway credentials, and separately confirmed the email notification was in fact agreed verbally and should be treated as in-scope. The system must touch only two rows: the SMS alerts row (`Blocked` → unblocked) and the email notification row (its conflict now has new evidence). The intake-form and DB-save rows must remain byte-identical, and the system must be able to prove that. Neither change commits without human approval.

### Repository and submission
- **Repository name:** `doctask-aditya-lingwal` (format: doctask-your-name; do NOT put "SuperDocs" in repo name — the system is yours, not theirs).
- **Visibility:** Private GitHub repository. Invite `github.com/o-kadam` as collaborator for review access.
- **Also include repo URL in the submission form** — insurance against expired invitations.
- Source: Task PDF, page 4 "Where It Goes."

## Task 2 — SuperDocs build requirements

### Assigned build card
- **Build:** Immigration Request-for-Evidence (RFE) response builder
- **Who it serves:** Immigration attorney responding to an officer's notice against a deadline
- **Difficulty band:** S3 (moderate — modest scope done immaculately beats ambitious half-finished)
- **Surfaces to touch:** Multi-document, search, chat, Review, export
- **Submission:** Pull request into public `superdocsapp/superdocs-builds` repository, `use-cases/` folder
- Source: Task PDF, page 5.

### Assigned build and objective
- Mandatory assigned build: immigration Request-for-Evidence (RFE) response builder for attorney-led document preparation.
- Goal is to support upload, retrieval, targeted drafting, human review, approval, and export on top of SuperDocs; this is not legal advice or eligibility decisioning.
- Strong output maps every officer request to a response section, cites source material accurately, and flags missing evidence explicitly.

### Required workflow steps
- Parse the officer notice into individual requests rather than a single generic summary.
- Retrieve relevant material from the original petition for each request.
- Draft concern-specific response sections; do not simply restate the original petition.
- Identify missing/new evidence needed, assemble the response package, and maintain a request-to-response coverage checklist.
- Route all proposed edits through human review/approval before export.

### Required platform contract
- Implement the four core SuperDocs actions: upload, targeted chat/edit instruction, approve, and export.
- REST or MCP are both acceptable integration paths; MCP is the strongest machine-interface option when practical.
- Proposed-change payload content may be JSON-encoded as a string and may require a second JSON parse before rendering.
- Long-running jobs can take from tens of seconds to minutes; show processing status and use retry-safe handling instead of premature failure.
- Exports do not consume operations, so frequent save/export checkpoints are acceptable.

### Bounded MVP and safety rules
- Use synthetic/public sample documents only; no confidential client files or private personal data.
- Missing facts must be marked as `not provided` or `needs attorney confirmation`; never invent evidence.
- Keep the product framed as attorney-support tooling with a mandatory human approval gate.
- Prior voice-agent legal intake experience is relevant background, but this build remains document-preparation support rather than legal decision-making.
- **Dev-mode quota protection:** small-sample mode (1-2 docs, limited sections) + stopping rule (max ~5 ops per dev run) so free-tier 500 operations last through development. Source: Task PDF, page 5-6 practical note #3.

### Optional depth and extra-credit
- Complete the assigned RFE build first; extra builds come only after the assigned flow is reliable.
- Optional paths include a build from the shared open list or an original SuperDocs-based idea informed by Task 3 research.
- Any extra build must be built on SuperDocs, not as a clone of SuperDocs.

## Task 2 submission and product guardrails

### Public submission mechanics
- Finished Task 2 builds go to a pull request in the public `superdocsapp/superdocs-builds` repository, inside the appropriate candidate folder under `use-cases/` or `extensions/`.
- Fork the repository, follow its `CONTRIBUTING.md`, add a README and screenshot in the candidate folder, and state that the build was created for the SuperDocs task.
- Put the candidate name in the PR description; never put email address or secrets in the public repository.
- The submission form, when emailed, is the only formal submission route; include the PR/link there and do not submit work by email attachment.

### Product rails for Task 2
- Do not build a SuperDocs clone, spreadsheet-editing product, document-management/archive product, live multiplayer cursor experience, or a workflow dependent on SuperDocs live-web browsing.
- Do not claim unavailable certifications, guaranteed/audited personal-data deletion, or rely on public roadmap items as shipped capabilities.
- Human-review any redaction or irreversible action; market it only as reviewed assistance, never a guarantee.
- Fictional clients and synthetic/public test data are expected; do not upload confidential, NDA-bound, or third-party private files.

### Quality bar applied to builds
- Tests should run without a live key; onboarding should support clone-to-working in minutes.
- Use idempotency for paid/costly operations, upload large files through the real upload path, never log/commit keys, and degrade gracefully on model or dependency failure.
- Prefer surgical changes, configuration over hard-coded special cases, measurable proof over assertions, and resumable/retry-safe operations.


## Task 3: Market-use-case research rules

### Required output
- Produce about ten specific, real-world SuperDocs use cases, each paired with companies that are plausible buyers.
- The goal is to identify a real buyer and concrete workflow, not merely list broad industries.
- A useful row should include: workflow/use case, buyer role/profile, named target companies, why SuperDocs fits, and known contact if any.
- `No known contact` is normal and acceptable; never fabricate a relationship, contact, or customer validation.

### Research honesty and assumptions
- Research-assisted hypotheses are acceptable when clearly labeled as hypotheses based on public research; do not present them as confirmed demand, customers, or personal knowledge.
- State the observable basis for each hypothesis: public company focus, documented workflow, role/job posting, product/service mix, regulated-document burden, or similar source.
- Separate `evidence` from `assumption`: evidence says why the company plausibly has the workflow; assumption says why it may buy or pilot this type of tool.
- Prior firsthand experience can be used where genuine, for example legal intake/qualification context, but it must still be described accurately and not overstated as immigration-document expertise.

### Strict outreach boundary
- Do not contact named companies, employees, prospects, or leads for this task. SuperDocs handles outreach.
- This is a market-thinking exercise, not a sales assignment; contacting people on SuperDocs' behalf fails the task.

### Suggested research workflow
- Use an AI research agent plus primary/public sources to generate a long list, verify named companies, and score each idea for document intensity, pain urgency, buyer clarity, and SuperDocs feature fit.
- Select the best ten diverse, defensible entries rather than forcing unsupported claims.
- Include the RFE-response/immigration-attorney workflow only as a carefully bounded hypothesis, framed as attorney-led document preparation rather than legal advice or eligibility decisioning.
- Strong Task 3 ideas can later become optional Task 2 extra builds, but Task 3 itself does not require building or contacting anyone.


## Task 4: Demo and communication assets

### Required deliverables
- Provide a short demo video, a one-page write-up, and a one-page architecture diagram.
- Task 4 is about clearly showing what was built, how it works, and what trade-offs were made.
- Claims in the write-up and demo must match what the working system actually shows.

### Demo video rules
- **Title and description must include "SuperDocs"** — mandatory per the brief.
- Target about 3 minutes; 5 minutes is the hard cap.
- Best demo shows the product doing real work on a real sample document flow, including edits/review/export.
- On-camera presence is optional; voice-over screen recording is acceptable.
- Do not show credentials, secrets, private/internal documents, or sensitive terminals on screen.
- If something sensitive appears, cover it with a solid box rather than blur.
- Upload the video to YouTube (public or unlisted) and also keep a copy in Google Drive.

### One-page write-up
- Explain what was built, who it is for, what result it produces, what trade-offs were chosen, and what the limitations are.
- Honest limitations are a positive signal; do not overclaim beyond the actual demo/system behavior.
- This is closer to an executive explanation than a long PRD.

### One-page architecture diagram
- Architecture here means a compact system/component flow diagram, not a full PRD package or exhaustive HLD/LLD document set.
- The goal is to make major components, data flow, integrations, review gates, and failure/retry points understandable at a glance.
- A single clear page is enough; visual clarity matters more than formal enterprise-document format.
- Supporting notes can exist elsewhere, but the required artifact is a concise one-page architecture view.

### Drive and submission reminder
- **All three artifacts — video, write-up, and architecture diagram — must have Google Drive copies.** Their links ride the submission form. Source: Task PDF, page 7.


## Coverage index
- Orchestration framework decision (LangGraph locked, LangChain boundary, 10-behaviour ownership split): covered — see "Orchestration framework decision" near the top.
- Task 1 scoping — **COMPLETE (2026-08-09)**. All eight locks recorded in the LOCKED sections under Task 1: deliverable (register), domain (software feature delivery), file formats, three-bucket type handling, three document types, register shape + blockers, request identity, request granularity, run scope, and the rules/playbook (rules file, R1–R4, finding shape, D1–D2, `No findings`). Next phase is architecture, not scoping: graph stages, MCP tool surface, watched-folder intake, idempotency on the project identifier, tests, and the synthetic corpus.
- Product familiarization and founder-research notes: covered.
- Task 1 brief interpretation, baseline floor, strong-submission behaviors, repo/readme/evaluation rules: covered.
- Task 2 assigned build, scope boundary, submission mechanics, product rails, optional paths: covered.
- Task 3 market-use-case research rules, evidence vs hypothesis framing, no-outreach boundary: covered.
- Task 4 demo/write-up/architecture deliverables: covered.
- Pending deeper walkthroughs or implementation planning can be added later without changing the brief notes above.

## Open Questions
No unresolved ambiguities requiring founder clarification as of 2026-08-08 audit. If any arise during build, they will be logged here before emailing hello@superdocs.app.

## Extra credit: scope and interpretation

### What it is
- Extra credit is optional; it is not a replacement for any core Task 1–4 deliverable.
- Only declare extra work when it is genuinely meaningful, demonstrable, and does not weaken the core submission.
- Keep it in the backlog until Task 1, the assigned Task 2 build, Task 3 research, and Task 4 presentation assets are complete and reliable.

### What qualifies
- Strongest fit: an additional build or integration that is genuinely built on top of SuperDocs.
- A Task 3 research idea can become an optional SuperDocs-based build.
- Meaningful SuperDocs API/developer-surface work created before the brief may also be relevant if it can be honestly demonstrated.
- A SuperDocs clone does not qualify as extra credit.

### Avoid assumption errors
- Do not assume that any unrelated external product automatically counts as Task 2 or as extra credit.
- Task 2 is explicitly a SuperDocs-based build; Task 4 is not a separate product-build task.
- Task 4 is the presentation layer for the submission: demo video, one-page write-up, and one-page architecture diagram for the work completed in Tasks 1–3/extra credit.
- An unrelated product could only be mentioned as background/portfolio context if the final form explicitly allows it; it cannot replace the required SuperDocs build.
- When uncertain, frame an item as `possible extra credit — confirm against final form/instructions` rather than asserting eligibility.


## Submission-wide operating rules

### Non-negotiable safety and honesty
- Never use confidential employer/client/NDA data, third-party private files, or real user credentials anywhere in the submission.
- Never fabricate capability, evidence, customer validation, legal certainty, security claims, or completion status.
- Prefer clearly labeled limitations, assumptions, and bounded demos over inflated claims.

### Delivery discipline
- Keep Task 1 private and Task 2 public via the required pull-request flow; do not mix their repositories or artifacts.
- Use screenshots, tests, sample data, and demos that are reproducible from the documented setup.
- Keep README, write-up, video, architecture diagram, and notes internally consistent so no artifact overclaims beyond another.


## Four written questions: capture plan

### The four prompts to answer later
- Prompt 1: what broke while using SuperDocs, including bugs, rough edges, and confusing moments.
- Prompt 2: if running the company, what single number/metric would be watched every morning, and why.
- Prompt 3: name the next five features in priority order, including what would be deprioritized or dropped to make room.
- Prompt 4: describe how day-to-day development and GTM operations would run themselves using concrete agentic loops, checks, and approvals.

### Evidence we should collect during the build
- Bug log with reproduction steps, expected behavior, actual behavior, impact/severity, screenshots, and whether it was reported through the expected channel.
- Candidate north-star metrics plus short justification notes on why each matters more than vanity metrics.
- Feature backlog with source evidence from real friction, user flow pain, or repeated operational cost.
- Notes on agentic operating loops: ownership, trigger, inputs, outputs, checkpoints, approval gates, escalation, and failure handling.

### Answering principles
- Use concrete evidence from actual usage of the tools/builds, not generic product opinions.
- Prefer honest specifics over polished vagueness.
- Keep answers grounded in trade-offs: what to prioritize, what to ignore, and why.
- Reuse Task 1 patterns where relevant for Prompt 4: resumability, verification, human approval, observability, and no false-success reporting.


## Working method recommended by the brief

### Suggested operating documents
- Maintain a `TASK.md` that tells coding agents/collaborators how to work in the repository: architecture boundaries, commands, safety rules, definition of done, and coding conventions.
- Maintain a `PROGRESS.md` that records assumptions, decisions, milestones, blockers, next steps, and any defended cuts.
- Record ambiguous choices and their rationale instead of leaving them implicit.

### Recommended execution pattern
- Make long-running work checkpointed and resumable so crashes or context resets do not destroy progress.
- Add a fresh-verifier pass separate from the primary implementer so blind spots are caught before submission.
- Before building a hard feature, define what the system must never do, write failure-oriented tests for that boundary, then implement the feature.
- Keep this method aligned with existing project rules: human approval gates, no false-success claims, observability, and retry-safe behavior.

### Interpretation
- These are recommended working practices from the brief, not a separate scored deliverable on their own.
- Even so, following them strengthens auditability, reproducibility, and final submission quality.
- Internal team/agent workflows can extend these practices, but should not conflict with the brief's safety and honesty constraints.


## What not to build: product rails and exceptions

### Disallowed product directions
- Do not build a spreadsheet-editing product; spreadsheets may be inputs or derived outputs, but not the core editor/product focus.
- Do not depend on SuperDocs live-web browsing as a core capability.
- Do not build a live multiplayer / visible-cursor collaboration experience or a workflow that requires it.
- Do not build a document-management/archive system as the main product.
- Do not claim or imply certifications/compliance statuses that the product does not currently have.
- Do not market audited/guaranteed personal-data removal or irreversible redaction guarantees; any redaction support must be human-reviewed assistance.

### Explicitly allowed exceptions
- Existing-provider e-signature integrations are allowed; building a native signature platform is not the point.
- Extracting PDF tables into spreadsheet-style output is allowed.
- A full OAuth authorization flow on the MCP surface is allowed.

### Source-of-truth and data rules
- Treat the task document/developer documentation as the source of truth, not marketing pages or roadmap language.
- Do not rely on roadmap or aspirational public statements as if they were shipped capabilities.
- Use fictional clients and synthetic/public/shareable data whenever examples, demos, or test corpora are needed.


## Known issues and bug-report discipline

### Expected reality
- SuperDocs is treated as a young product with real rough edges/bugs; discovering and reporting them is a positive signal, not a penalty by itself.
- Blocking platform issues can justify deadline consideration when reported promptly and clearly.

### Bug-report format to follow
- Record what action was taken, what was expected, what actually happened, severity/impact, and a reproduction artifact such as screenshot or sample file.
- Report bugs through the intended product/reporting channel and keep a parallel internal bug log for later written answers.
- Mark truly blocking issues clearly and early rather than silently working around them.

### Safety implication
- Review mode is helpful but not an absolute guarantee; irreversible actions such as redaction/final export still require human verification.
- Build workflows should preserve this assumption and avoid irreversible automation without review.


## Conduct and disqualification-risk rules

### Strict conduct boundaries
- No astroturfing: do not create fake accounts, coordinate artificial engagement/upvotes, solicit fake or incentivized reviews, or create a false impression of real-user demand.
- Never expose API keys, credentials, secrets, or tokens in repositories, commits, screenshots, logs, terminals, chat, Discord, or public posts.
- Do not attempt prompt injection against review tooling; attempting it is disqualifying regardless of success.

### AI-use disclosure
- Heavy AI use is allowed and can be a positive signal, but it must be disclosed honestly.
- Maintain one human applicant/account; do not submit or coordinate multiple applications as if they were independent people.
- Record approximate AI contribution and how the AI was directed, verified, and constrained for the final form.

### Public-facing communication
- If posting publicly, favor quality over volume and disclose candidate status where relevant.
- Demo, README, and written work must remain understandable in the candidate's own voice because live discussion/modification may be expected.

### Practical repository hygiene
- Use `.env`-style local configuration, `.gitignore`, fake test keys, secret scanning, and screenshot checks before every publish/PR.
- Treat secrets hygiene as a release gate, not a cleanup task.


## What SuperDocs promises and upload boundaries

### Candidate ownership and participation boundaries
- The work remains the candidate's own project and portfolio work; it is not unpaid sales work for SuperDocs.
- SuperDocs will not ask candidates to contact companies, chase leads, or post content they are uncomfortable posting.
- If SuperDocs wants to feature a build, it will ask first and provide attribution; declining does not affect evaluation.

### Upload/data rules
- Allowed uploads: documents owned by the candidate, public documents, or synthetic/fabricated test documents.
- Prohibited uploads: NDA-bound employer materials, confidential files, third-party private documents, real prospect/client documents, and real personal health data.
- The service is hosted in the United States; account for that fact when deciding what may be uploaded.

### Accommodation meaning
- An accommodation is a reasonable adjustment that helps someone complete the task fairly when a disability, health condition, access barrier, caregiving constraint, or other legitimate circumstance affects the normal task process.
- Examples can include extra time, an alternative communication format, a different demo/presentation arrangement, or another reasonable accessibility adjustment.
- The brief invites candidates to request needed accommodation by email and states that doing so will not count against them.


## Submission flow and final delivery rules

### Three submission destinations
- Task 1 shared agentic system: private GitHub repository with `o-kadam` added as collaborator.
- Task 2 SuperDocs builds: public pull request to `superdocsapp/superdocs-builds`.
- Videos, Task 3 research, write-up, architecture diagram, answers, and other public links: submitted via the final Google Form using link-based delivery.

### Formal submission rule
- The Google Form is the only formal submission channel.
- Do not treat email replies or attachments as the actual submission path; email is for task questions and bug/blocker reporting.
- A form invitation is expected by email, and work should be organized so links are ready when it arrives.

### Public PR hygiene
- For Task 2, fork the public repo, add the build in the correct candidate folder, include README and screenshot, and put the candidate name in the PR description.
- Do not put email addresses or secrets in the public repository/PR.
- A merged PR is attribution/publication, not a hiring guarantee.

### Timing interpretation
- Early submission does not create a special fast-track advantage.
- The practical goal is to submit a complete, honest, reproducible package before the cutoff accepted by the final form.


## Optional public publishing and tagging

### Publication rules
- Public posts are optional and are not a required or graded deliverable.
- If publishing on LinkedIn, X, YouTube, Medium, dev.to, Hashnode, or a public repository, make only claims personally verified through actual product use/build evidence.
- Disclose candidate affiliation/status where relevant and prioritize quality over posting volume.
- Tagging `@superdocsapp` on X/LinkedIn is recommended when relevant, but does not replace final-form submission.
- Include public post links in the final Google Form so they can be found even without platform tagging.


## Help and official communication channels

### Support path
- Check official SuperDocs documentation first for integration/setup questions.
- Use `hello@superdocs.app` for task-specific questions, genuine blockers, accommodation requests, bug reports, and official task-document corrections; identify the relevant task clearly.
- Do not rely on social-media DMs for task support.

### Shared-space boundary
- Discord can support candidate-to-candidate discussion, but do not disclose or discuss Task 1 solution details in shared channels because Task 1 is private for fairness.
- Use official email for task-specific clarification rather than sharing private-task content publicly.


## Final quality bar and live-review readiness

### What happens after submission
- Every completed submission is personally reviewed; completing candidates receive a written personal reply.
- Strong submissions may lead to a direct conversation where the build is reviewed and modified live; this is a collaborative review, not another technical exam.
- Keep code, README, demo, diagram, and write-up aligned with work that can be genuinely explained and changed live.

### Five universal strong-submission behaviors
- Honesty over fabrication: flag unsupported claims and gaps; never invent facts.
- Surgical precision: change only intended content and demonstrate preservation of untouched content.
- Configuration over code: new rules, clients, courts, and formats should be data/config changes rather than rewrites.
- Proof over assertion: measure completeness, preservation, timing, and other claims rather than merely stating them.
- Graceful re-entry: resume after crashes without losing work or duplicating side effects.

### Definition of done: engineering checklist
- Real tests run without a live key; a fresh clone reaches working state in minutes.
- Error messages identify cause and practical fix.
- Costly operations are idempotent.
- Large real files use the upload path, not an in-memory-only shortcut.
- Keys never appear in logs, commits, screenshots, or shell history.
- Model/dependency failures degrade gracefully instead of killing the system.
- For measurements: state method before result, report variance, commit raw data, report tail behavior (not just averages), and state limits.

### Deeper engineering standard
- Fix the class of problem, not only the observed test case; validate against plausible sibling cases.
- Keep intelligence in decision-making/orchestration and code in execution; avoid a pile of hard-coded special cases masquerading as intelligence.
- Do not delete a feature to hide a bug, defer a failure and call it fixed, or fix before investigation.
- Deliberate hard-coded safety defenses can complement intelligent logic when they protect a known boundary.
- A fix must not reject valid work elsewhere; if claiming something cannot be done, provide evidence rather than relying on difficulty.
- Explicitly documenting where the build fails is a credibility signal. For unverifiable figures, detect and surface the uncertainty rather than claiming correctness.

### Scope and evaluation mindset
- A modest build completed immaculately beats an ambitious, incomplete build.
- Optional work can only add; skipping it does not count against the submission.
- Reported SuperDocs bugs earn credit.
- Zero is a safe truthful answer where applicable; class projects count as real experience; criticism is rewarded.


## Final FAQ clarifications and closing reminders

### Evaluation and responsibility
- This task replaces additional technical interview rounds; strong work may lead to a direct discussion/live review, but a job is not guaranteed.
- Evaluation is work-based rather than filtered by location or personal details.
- If a coding agent creates/uses an account, the human operator remains responsible for the account and compliance.

### Platform and data clarifications
- Uploaded documents are stored to run the service on U.S.-hosted infrastructure; accounts/documents are isolated and are not used for AI-model training according to the brief.
- Check current docs before classifying a capability as missing; review mode, version history/revert, live progress, citation preservation through edit/export, and agent self-signup may already exist.
- Free/promo operation details noted in the brief: one operation may cover up to 25 sections of targeted edits; exports/downloads are free; searches use operations; stopped/errored edit requests are not billed.

### Final condensed reminders
- Keep work separated across the three designated submission destinations and use the final form as the only formal submission channel.
- Use the official support channel for questions, report bugs constructively, and keep public claims verified.
- Honesty, reproducibility, and demonstrated evidence beat theater, inflated claims, or unnecessary scope.


## Audit correction and missing brief requirements

### Task 1 domain and deliverables
- Pick a domain the candidate genuinely knows and can stand behind; supported examples are contracts, plans/status reports, loan files, insurance claims, and clinical paperwork.
- Core deliverable can be a grounded register, brief, or report. Every claim must trace to an exact source location.
- Human approval/rejection applies to conflicts, findings, and incremental updates before they commit.
- A watched location is required for arriving documents; each arrival must cause a focused, low-cost update rather than an equivalent full rerun, preserve unaffected output exactly, surface contradictions, and answer what changed/when/because of which source.

### Task 4 details corrected
- Video title and description must include `SuperDocs`.
- One round-wide video is the default; separate short videos per build are also accepted.
- The Drive copy may be used by SuperDocs to host a featured video with credit, subject to the candidate's consent choices in the form.
- The one-page write-up and one-page architecture diagram are uploaded to Drive and their links are submitted in the form.

### Final form completeness
- Form is expected to collect: all relevant links, GitHub handle, four written answers, bugs/issues, AI-built percentage and direction method, honest works/does-not-work self-report, Task 3 list, write-up, architecture diagram, feature-consent choices, optional name idea, and extra-credit entry.
- Optional platform-name suggestion: document/AI-related, simple, easy to spell aloud; use may receive credit and an Amazon gift card.

### FAQ correction
- Job/company registration and new-AI-technique exploration are contextual FAQ answers, not implementation requirements.
- Prior note suggesting personal details generally do not affect evaluation is superseded by the brief's narrower statement: location does not filter; the work decides.


## Recommended next audit artifact

### Traceability matrix to prepare next
- Create a final traceability matrix mapping each major brief section/page cluster to the corresponding notes section.
- For every line item, label it as `mandatory brief requirement`, `optional/extra-credit`, `implementation recommendation`, or `open decision`.
- Use this matrix as the penalty/rejection audit sheet before planning with other agents.
- Goal: make it obvious that no brief requirement is missing, no recommendation is misread as a requirement, and no duplicate/conflicting note survives into implementation planning.

