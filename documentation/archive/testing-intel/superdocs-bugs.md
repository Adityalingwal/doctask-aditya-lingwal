# SuperDocs API + MCP — Bug Findings

Used Claude Code and Codex to test SuperDocs. Both agents tested across the REST API and the full MCP tool sweep, and found **11 reproducible bugs** — 1 high, 7 medium, 3 low.

Everything was run on a free account under my email, **lingwaladitya82@gmail.com**. You can check the logs in this account.

## Findings summary

| ID | Severity | Surface | Title |
| --- | --- | --- | --- |
| **H-1** | High | REST + MCP / billing | A no-change edit sometimes still charges 1 operation |
| M-1 | Medium | REST | A made-up `approval_mode` value is accepted and silently auto-applies the edit |
| M-2 | Medium | HITL async | A proposed change shows a "nothing changed" diff while claiming the edit was made |
| M-3 | Medium | REST / docs | The approve/deny shapes in the docs don't work as written |
| M-4 | Medium | REST doc-events | A one-paragraph save reports every paragraph as brand-new |
| M-5 | Medium | MCP | Opening two documents into one session keeps only one |
| M-6 | Medium | MCP | `delete_attachment` returns HTTP 500 and leaks an internal error |
| M-7 | Medium | MCP / architecture | Coarse chunks wipe out compact-mode savings and duplicate content on insert |
| L-1 | Low | MCP / docs | `focus_session_document` rejects the UUID its own description says it accepts |
| L-2 | Low | MCP prompts | The 4 workflow prompts handle missing optional arguments inconsistently |
| L-3 | Low | REST | A one-word message sometimes triggers a full unwanted document |

Counts: **1 High · 7 Medium · 3 Low.**

---

## High

### [H-1] A no-change edit sometimes still charges 1 operation
**Severity:** High · **Where:** REST API + MCP server (billing)

**What broke:** When you ask the AI to make a change the document *already* has — so there is genuinely nothing to do — SuperDocs is supposed to charge 0 operations. Sometimes it does, sometimes it charges 1 operation for zero work. The billing is not consistent.

**SuperDocs' own promise (docs, 2026-07-17):** "an edit request the document already satisfies… changes nothing, and bills 0."

**What Claude Code found (REST API only):**
Claude Code sent several messages to the REST API and checked the bill after each one:
- It sent the message *"Translate this document into English"*, but the text was already in English. The SuperDocs AI correctly replied that nothing needed changing and made 0 edits → **still charged 1 operation.**
- It sent a plain *"start"* message, which is not an edit request at all → 0 edits → **charged 1 operation.**
- It sent *"Leave the document exactly as it is"* → 0 edits → **correctly charged 0.**
- It sent *"Make sure it ends with a period"*, and the text already ended with a period → 0 edits → **correctly charged 0.**

Four messages, all ending in zero changes — yet two were billed and two were not.

**What Codex found (an edit through MCP, then the same request through REST):**
1. Codex called the **MCP** `chat` tool and, to make a genuine change first, sent it the instruction *"Change the Conclusion paragraph to: This conclusion is stable."* The SuperDocs AI performed that edit. The account went **34 → 35** operations — a correct charge, because a real change happened.
2. Codex then sent the **same instruction** to the REST endpoint `POST /v1/chat`. The document already had that exact text, so there was nothing left to change.
3. The AI honestly replied *"No changes were necessary"* and returned the **same version_id** (proof nothing changed) — but the bill was **`ops_charged: 1`**. The account went **35 → 36.**
4. Codex sent that same REST request **once more** — this time it charged **0**, which is correct. So the wrong charge happens only on the *first* REST request after the MCP edit. Codex reproduced this twice.

**The actual bug:** The same kind of "there is nothing to change" request is billed inconsistently — sometimes 1 operation, sometimes 0. Claude Code saw it on the REST API by itself (some no-change messages billed, some didn't). Codex saw it between the two surfaces (a no-change REST request right after an MCP edit billed 1, a repeat billed 0). It's the same underlying problem found two independent ways: a request that changes nothing does not reliably bill 0, even though the docs promise it will.

---

## Medium

### [M-1] A made-up `approval_mode` value is accepted and silently auto-applies the edit
**Severity:** Medium · **Where:** REST API (`POST /v1/chat`, review-workflow validation)

**What broke:** `approval_mode` controls whether an edit is applied automatically or held for a human to approve first. If you send a value that isn't one of the two allowed ones, SuperDocs should reject the request. Instead it accepts the junk value, treats it as "auto-approve", applies the edit right away, and bills for it.

**What the docs say:** There are exactly two valid approval modes — `approve_all` and `ask_every_time`.

**What Codex found:**
1. Codex sent `POST /v1/chat` with a real edit instruction — *"Change only the Introduction paragraph to say: Welcome to the 2026 QA report v2. Do not alter anything else."* — and set `"approval_mode": "banana"` (a value that does not exist).
2. The server returned **HTTP 200**. The SuperDocs AI applied the edit immediately with `status: "auto_approved"` and billed **1 operation** (account went 36 → 37 used).
3. To confirm the endpoint *can* reject bad values, Codex sent a different junk value on a separate request — `"response_mode": "banana"` — and it was correctly rejected with **HTTP 422**. So the validation clearly works; it just isn't applied to `approval_mode`. (Invalid `model_tier` and `thinking_depth` values were also accepted, on no-change turns that billed 0.)

**The actual bug:** A typo in the `approval_mode` field doesn't fail — it silently switches an intended "ask a human every time" workflow into "auto-apply everything." The document gets changed before anyone realises. A validation error would have been recoverable; silent defaulting is not.

### [M-2] A proposed change shows a "nothing changed" diff while claiming the edit was made
**Severity:** Medium · **Where:** REST API (`POST /v1/chat/async`, human-in-the-loop approval)

**What broke:** In the human-in-the-loop flow, the AI proposes a change and a person reviews the before/after diff before approving it. In one case the proposed diff pointed at the wrong part of the document and showed no actual difference (before text = after text), yet the explanation confidently said the requested edit had been made.

**What Codex found:**
1. Codex started an async chat job with `"approval_mode": "ask_every_time"` and the instruction *"Change only the Metrics table Status value to reviewed. Do not alter anything else."*
2. It polled until the job reached `awaiting_approval`, then looked at the pending change.
3. The pending change targeted the **Metrics heading** chunk, and its `old_html` was identical to its `new_html` — a no-op. But the `ai_explanation` read: *"I've updated the 'Status' value in the Metrics table to 'reviewed', while keeping the rest of the table structure and content unchanged."*
4. Codex denied that proposal with feedback. The SuperDocs AI then generated a **correct** second proposal against the real table chunk (changing `<strong>unchanged</strong>` to `<strong>reviewed</strong>`) — proving the edit was possible; the first proposal was simply wrong.

**The actual bug:** A reviewer approves based on the diff they see. A no-op diff paired with a confident "done" explanation can get a reviewer to approve a change that does nothing — or create false audit evidence that a value was reviewed and updated.

### [M-3] The approve/deny shapes in the docs don't work as written
**Severity:** Medium · **Where:** REST API (human-in-the-loop approval endpoint) + docs

**What broke:** The docs describe how to approve or reject a proposed change. Following the documented shapes either fails outright or reports success while quietly leaving the job stuck open. Both agents hit this, in two different ways.

**What the docs say:** "respond `approved=true|false` plus optional feedback," and "for single changes, set `approved=true/false`."

**What Claude Code found (the bare deny is rejected):**
- Claude Code sent the documented shape to reject a change — just `{"approved": false}`.
- The server returned **HTTP 422 "job_id Field required."**
- In practice you have to send `{job_id, change_id, approved}` — fields the docs don't mention. Anyone integrating straight from the docs cannot reject a change.

**What Codex found (the documented single-change deny leaves the job stuck):**
1. With a job waiting for approval, Codex sent the documented top-level shape: `{job_id, approved: false, feedback}`.
2. The response was `{"status": "ok", "message": "Approval processed", "batch_complete": false}` — looks like success.
3. But polling the job showed it **still `awaiting_approval`**, with the same pending change and `pending_batch_decisions: null`. Nothing actually happened.
4. Only the per-change array form worked: `{job_id, approved: false, changes: [{change_id, approved: false, feedback}]}` → response `batch_complete: true`, and the job finally completed.

**The actual bug:** A client following the docs either gets a 422 (Claude Code's bare deny) or a fake-success that leaves the review loop stuck open (Codex's single-change deny). The shape that actually works — a per-change array with `job_id` and `change_id` — isn't the one documented. (Denying without feedback does complete cleanly; denying *with* feedback re-proposes a revised change by design, which is expected and only a minor UX note.)

### [M-4] A one-paragraph save reports every paragraph as brand-new
**Severity:** Medium · **Where:** REST API (non-AI save + cross-session `doc-events`)

**What broke:** When one session saves a small manual edit, other sessions watching the same document get a change feed (`doc-events`) telling them what changed. A save that touched exactly one paragraph reported *every* chunk in the document as freshly created, losing the information that only one paragraph actually changed.

**What Codex found:**
1. Document D1 was open in two sessions (S1 and S3). In S1, Codex called the non-AI save endpoint `POST /v1/sessions/{sid}/documents/doc_primary/save`, sending full document HTML where only the Conclusion paragraph differed, and `touched_chunk_ids` listing just that one paragraph's chunk id.
2. From S3, Codex polled `GET /v1/sessions/{sid}/doc-events`.
3. The event reported **all 7 chunks** with `operation: "create"` and `old_html: null`, and `changed_chunk_ids` listed every chunk — even though only one paragraph changed and only one chunk id was named in `touched_chunk_ids`.
4. This happened on two separate saves, so it isn't a one-off.

**The actual bug:** A second session watching `doc-events` cannot tell a one-paragraph edit apart from a full-document replacement. That leads to unnecessary whole-document reloads, noisy conflict handling, misleading audit logs, or accidental overwrites in any integration that applies these event diffs incrementally.

### [M-5] Opening two documents into one session keeps only one
**Severity:** Medium · **Where:** MCP server (session / document management)

**What broke:** You should be able to open two saved documents into a single MCP session and have both available as tabs. Instead, only one survives — the last one in the list wins and the earlier one is silently dropped.

**What the docs say:** the first document listed is the focused one.

**What Claude Code found:**
1. Claude Code called both `init_session(document_ids=[A, B])` and `open_documents(session, [A, B])`. Both echoed back `opened: [A, B]`, as if both were attached.
2. But the session roster's `documents` array held **only one** document (slot `doc_primary`) — document B, the last id. Document A was silently gone. And `focused_document_id` pointed at B, contradicting the docs' "first is focused."
3. Proof it wasn't just a display glitch: calling `focus_session_document` on the dropped document A returned **HTTP 404 "not open in this session."** Only one document was genuinely attached.
4. The `doc_primary` slot even resolved to different underlying documents across calls (unstable aliasing).

(REST multi-document, where the second doc was created via `/documents/blank`, worked earlier — this specific problem is the *open-saved-documents* path over MCP.)

**The actual bug:** You cannot hold multiple saved documents as tabs in one MCP session. That breaks the marketed cross-document / multi-tab workflows on the exact agent-native surface this role is about hardening.

### [M-6] `delete_attachment` returns HTTP 500 and leaks an internal error
**Severity:** Medium · **Where:** MCP server (attachments)

**What broke:** Deleting an attachment that has finished processing should either succeed or fail with a clean error. Instead it crashes with an HTTP 500 and leaks a raw Python error message to the client.

**What Claude Code found:**
1. Claude Code uploaded an attachment and waited for it to finish processing (status ready/completed).
2. It then called `delete_attachment` — tried both by `attachment_id` and by `job_id`.
3. Both returned **HTTP 500** with the message: *"Failed to cancel attachment: 'Job' object has no attribute 'get'"*. That is an unhandled Python `AttributeError` leaking through — the delete path assumes a still-processing job (a plain dict with `.get`), but a completed `Job` object doesn't have `.get`.

**The actual bug:** A finished attachment can't be deleted over MCP at all — the call hard-crashes with a 500 and exposes internal implementation detail. On the agent-native surface, an unhandled 500 like this undercuts the "agents can run unattended" story.

### [M-7] Coarse chunks wipe out compact-mode savings and duplicate content on insert
**Severity:** Medium · **Where:** MCP server (chunking) — ties to the 97%-token-savings claim

**What broke:** SuperDocs splits a document into "chunks" so an edit only re-sends the chunk that changed (compact mode), which is where the big token savings come from. But AI-*created* documents come back as a few huge multi-section chunks. That means a tiny edit re-sends a whole four-section block, and inserting a new section can duplicate an existing one.

**What the docs say:** compact-mode edits re-send only the touched chunk, and the token savings can reach 97%.

**What Claude Code found (two symptoms, one root cause):**

*Savings blunted:*
1. Claude Code had the SuperDocs AI create a Statement of Work via the `chat` tool. Its Sections 1–4 (Overview + Scope + Timeline + Fees) all came back as a **single** `data-chunk-id`.
2. Claude Code then sent a compact-mode edit (`response_mode: "compact"`) changing just two numbers in the Fees section. Because those numbers live inside the one giant chunk, the compact diff had to re-send that **entire four-section chunk** as both `old_html` and `new_html` — near-zero token savings. (`updated_html` was correctly `null`; the coarse chunk defeated the saving anyway.)
3. Contrast: the uploaded 22-page docx parsed into **313 fine chunks**, where compact mode genuinely pays off. The same SOW content was 5 chunks as AI-created versus 16 chunks after export-then-reimport — the granularity depends entirely on how the document was made.

*Content duplicated on insert:*
1. Because Fees is buried inside the mega-chunk, Claude Code sent a simple human-in-the-loop request *"add a Confidentiality section after Fees."*
2. The only insert boundary was *after* the whole mega-chunk, so the SuperDocs AI produced a `create` that **re-included the entire Fees section** and then appended Confidentiality.
3. After approval, a `txt` export showed **"Fees and Payment Terms" twice** — the whole fee table was duplicated. (`revert` removed it cleanly, which is the saving grace.)

**The actual bug:** The 97%-savings claim is real but conditional on chunk granularity, and coarse chunks can cause visible document corruption on a trivial insert.

---

## Low

### [L-1] `focus_session_document` rejects the UUID its own description says it accepts
**Severity:** Low · **Where:** MCP server (tool description vs behaviour)

**What broke:** The `focus_session_document` tool's own description says it accepts either the session slot id *or* the durable `documents.id` UUID. In practice, passing the durable UUID fails.

**What Claude Code found:**
- Passing the durable document UUID to `focus_session_document` returned **HTTP 404**.
- Only the slot id `doc_primary` worked.

**The actual bug:** The tool description promises something the tool doesn't do, so an integrator following it hits a 404. (Related to M-5.)

### [L-2] The 4 workflow prompts handle missing optional arguments inconsistently
**Severity:** Low · **Where:** MCP server (workflow prompts, tested via raw JSON-RPC `prompts/get`)

**What broke:** SuperDocs ships 4 workflow prompts. When you leave out an optional argument, some prompts insert an explicit "ask the user first" placeholder (good), while others silently fill in a hardcoded default with no hint that they did — and the behaviour differs from one argument to the next inside the same server.

**What Claude Code found:**
- `draft_from_outline`, `edit_styled_docx`, and `review_contract_for_redflags`'s `focus_areas` all render an explicit ask-the-user-first placeholder when the argument is omitted — the good pattern.
- But `convert_format` **silently defaults `target_format` to "pdf"**, and `review_contract_for_redflags` **silently defaults `viewpoint` to "buyer"** — no note that it's an assumed default, no ask-first instruction.
- (This was read-only: `prompts/get` returns a template; it doesn't execute an edit or bill an operation.)

**The actual bug:** An agent that calls `convert_format` with no format silently ships a PDF the user never chose; the red-flag review silently adopts the buyer's side. It doesn't crash, but the inconsistency is a genuine agent-reliability gap.

### [L-3] A one-word message sometimes triggers a full unwanted document
**Severity:** Low · **Where:** REST API (chat) — **intermittent; labelled honestly**

**What broke:** Sending the vague one-word message *"start"* on a tiny document once made the SuperDocs AI generate a whole document the user never asked for. It did not happen every time, but it happened.

**What Claude Code found:**
- Claude Code sent the message *"start"* on a tiny `<h1>Doc A</h1>` document. The SuperDocs AI **generated a full 19-section "Business Services Proposal"** out of nowhere.
- On a clean re-test, the same *"start"* message just got the reply *"I'm ready, how can I help?"* with no generation.

**The actual bug:** Ambiguous one-word input is handled inconsistently — usually the AI correctly waits, but once it silently produced a whole document a user never wanted. It is non-deterministic, which makes it harder to catch and worse for trust, not less real: a user could get a surprise full rewrite. (That conversational *"start"* reply also billed 1 operation — folds into H-1.)
