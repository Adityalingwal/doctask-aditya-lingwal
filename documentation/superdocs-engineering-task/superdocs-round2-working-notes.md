# SuperDocs Round 2 — Working Notes

## Technology Stack (All Tasks)
- **Backend:** Python + FastAPI
- **Agent orchestration:** an agent framework such as LangGraph or LangChain; AutoGen, CrewAI or a hand-rolled loop count as comparable. Our choice and its reasoning: `DECISIONS.md`.
- **Database:** PostgreSQL + pgvector (vector search for retrieval; also hosts the LangGraph checkpointer — one DB, not two)
- **Review interface:** React
- **Machine interface:** MCP server (strongest version of behavior 4; founder's own stack)
- Source: Task PDF, page 3 "The Stack." Stack deviation allowed with reasoning documented in write-up. No deviation taken — LangGraph is explicitly named in the brief.

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
- Har non-obvious decision ko build ke time turant log karna hai — **`DECISIONS.md` mein, is file mein nahi.**
- Format: `date | decision | reason | trade-off | proof/link | follow-up`.
- Yeh log README, write-up, demo script aur founder discussion ke source material ke roop mein use hoga.

## Notes-file rules
- Notes should separate confirmed brief requirements from planning assumptions or implementation ideas.
- Any assumption must be labeled clearly as an assumption/hypothesis, not as a brief requirement.
- Use synthetic/public/shareable data only throughout examples, demos, tests, and screenshots.
- Preserve founder-recommended defaults first; document deviations only with explicit rationale.
- Prefer honest gaps/limitations over inflated claims.
- When a section is covered, keep one compact checklist so future sanity checks can quickly verify completeness.

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
- Human har finding ko **approve ya reject** kar sake (page 2 — bas yahi do); same review session mein mixed decisions support hone chahiye, aur rejected item ko change karne par unrelated approved findings preserve rehne chahiye.

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

### Incremental updates and auditability
- System one-time analyzer nahi hai; new documents/case updates aane par report ko alive rakhna hai.
- Watched location/folder ya chosen intake mechanism se new file detect/ingest karna hai.
- Sirf new file aur usse affected facts/findings ko process karna hai; full re-analysis/rewrite default nahi hona chahiye.
- Focused update proposal banana hai. Unaffected report sections exactly unchanged rehne chahiye, aur system ko is invariance ka proof dena chahiye.
- New source existing claim/finding ko contradict kare to conflict surface karna hai; silently overwrite/decide nahi karna.
- Human approval ke bina update commit/export nahi hoga.
- Audit trail answer de sake: kya badla, kab badla, aur kis source document/evidence ki wajah se badla.

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
- **All decisions now live in `DECISIONS.md`**, not here. This file holds the brief's requirements; that file holds our choices. Task 1 scoping is complete as of 2026-08-09 — the next phase is architecture (graph stages, MCP tool surface, watched-folder intake, idempotency, tests, synthetic corpus).
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

