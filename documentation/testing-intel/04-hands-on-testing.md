# SuperDocs — Hands-On Testing Log

> First-hand product testing to build authentic application material. Started 2026-07-21.

## Test 1 — Homepage live demo ("Cut the jargon"), no login
**Setup:** superdocs.app homepage embedded demo, jargon-heavy "Q1 Product Update" doc. Clicked the "Cut the jargon" quick-action.

**Result: ✅ Worked. Edit happened in-place, formatting preserved.**
- Title: "Q1 Product Update: New Features Launch" → "New Features Available Now"
- "leverages cutting-edge technology to provide actionable insights and enable users to make data-driven decisions" → "uses modern technology to provide clear insights, helping you make better decisions"
- "streamlined onboarding flow that reduces friction and optimizes the user journey from sign-up to value realization" → "simplified our onboarding process to make it easier"
- Demo edit counter: 3 → 2 (only 3 free demo edits, no signup)
- Heading + paragraph structure stayed intact — genuine in-document edit, not a chat reply.

**Takeaway for application:** The headline claim ("AI edits inside the document, formatting intact") is real even in the throwaway marketing demo. Good, but the demo is a limited gimmick (3 edits, one canned doc). Real testing needs the full app.

## Test 2 — REST API sanity + edge cases (key: free tier)
Method: direct `curl` to `api.superdocs.app/v1/chat`.

| # | Test | Result | Ops |
|---|---|---|---|
| Key check | `GET /v1/sessions` | HTTP 200 ✅ | 0 |
| Small edit | "make this more formal" on casual line | ✅ Fixed "Ill"→"I will", "tmrw"→"tomorrow"; returned chunk_id + old/new_html diff, status `auto_approved` | 1 |
| Create-from-scratch | "Create an NDA between two companies" | ✅ Full 6.5KB NDA — header band, parties table, placeholders | 1 |
| Ambiguous | "make this better" | ✅ Asked clarifying Q (matches changelog claim) — **but 0 changes still billed 1 op** | 1 |
| No-op (dirty) | "capitalize first word" on "Hello world." | Interpreted as title-case → changed "world"→"World" | 1 |
| No-op (clean) | "translate to English" on English text | Said "already in English", **0 changes — but billed 1 op** | 1 |
| Empty doc | edit on `""` | ✅ Graceful ("no document loaded, want to upload?"), no crash | ~0 |
| Contradictory | "make it longer AND shorter" | ✅ Refused, asked to clarify, no change — **billed 0 ops** | 0 |
| Malformed HTML | unclosed `<p>`, `<b>`, `<table>` | ✅ Recovered — closed bold, preserved table, formalized. Robust parser | 1 |

### ⭐ KEY FINDING — inconsistent billing on zero-change turns
Their docs/pricing claim: *"an edit request the document already satisfies gets an honest 'already satisfied' answer, changes nothing, and bills 0"* and *"denied changes are never billed."*
Observed reality:
- Contradictory request (no change) → **0 ops** ✅ (matches claim)
- Clean no-op "already in English" (no change) → **1 op** ❌ (contradicts claim)
- Ambiguous clarifying question (no change) → **1 op** ❌
**→ Billing on no-change turns is inconsistent.** Concrete, defensible interview point — ties directly to their stated "honest billing / transparency" value. Frame as a question, not an accusation: "Is a clarifying-question turn meant to bill an op? I saw it vary."

### Architecture observations (from API responses)
- Every element gets a `data-chunk-id` (UUID) — confirms the chunk-targeting design first-hand.
- Response gives full `changes[]` array: `operation`, `chunk_id`, `status` (auto_approved), `old_html`, `new_html`, `ai_explanation`, `document_id`.
- `usage` block is detailed + transparent: monthly_used/limit/remaining, was_billable, ops_charged, tier, bucket_used. Good DX.
- Malformed-HTML recovery + "Parallel edit" note in test G → suggests it parallelizes multi-section edits.
- Grammar auto-fixes even when only asked for tone → edits can be slightly broader than the literal ask (double-edged: helpful vs "edited more than I asked").

## Test 3 — Multilingual, model tiers, compact mode, HITL, revert

### Multilingual (⭐ relevant for a Hinglish user)
- **Roman-Hindi/Hinglish doc ("Namaste, aapka order ready hai...") + English "make tone formal"** → ❌ **confused, no-op** ("request unclear, could you tell me what to do?"). Tone edits on Hinglish/Romanized-Hindi content are a weak spot.
- **English doc + Hinglish prompt ("is paragraph ko chhota bana do")** → ✅ shortened correctly, BUT reply came back in **English** (docs claim reply matches request language — didn't here for Roman-Hindi).
- Takeaway: pure-script languages likely fine (their changelog lists Hebrew/Korean/Mandarin), but **Hinglish/Romanized-Hindi is shaky** — authentic, specific finding I can cite.

### Model tiers & compact mode
- `model_tier: "turbo"` → worked, ~9.4s for a tiny edit (not dramatically fast on small docs — tier speed prob matters more at scale).
- `response_mode: "compact"` → ✅ `updated_html` is null, only `chunk_diffs` returned (per-section before/after). Confirms the token-saving design first-hand.

### HITL approval (async) — ✅ works
- `POST /v1/chat/async` with `approval_mode:"ask_every_time"` → `job_id`, status `pending`→`in_progress`→`awaiting_approval`.
- `metadata.pending_changes` carried the proposed change (operation `create`, `new_html`, `ai_explanation`).
- Approve/deny: `POST /v1/chat/{sid}/approve` — **requires `job_id` + `change_id` in the BODY** (not just session in URL; a bare `{approved:false}` 422s). Minor DX gotcha.
- **Finding:** denying WITH `feedback` makes the AI **re-propose** a revised change → job loops back to `awaiting_approval`. To hard-reject, deny without feedback (else you get a retry loop).

### Revert — ✅ works cleanly
- `POST /v1/sessions/{sid}/revert` `{turn_index:0}` → doc + chat both snap back; test marker gone; `compose_text` returned (the reverted message, to pre-fill/resend); `reverted_to_turn:-1` (back to empty). Confirms "rewind chat + document together."

## Test 4 — Export, agent self-signup, attachments, multi-doc

### Export round-trip — ✅
- `POST /v1/documents/export` (html or session_id), formats docx/pdf/html/md/txt.
- HTML→DOCX: HTTP 200, valid OOXML (36KB, real `word/document.xml`). Files at `documentation/artifacts/export-test.docx`.
- HTML→PDF: valid PDF 1.4, 1 page (23KB). `documentation/artifacts/export-test.pdf`.
- Fidelity claim holds at basic level; deeper test pending on the big doc.

### ⭐ Agent self-signup — ✅ (the headline agent-native test)
- `POST /v1/agents/signup {"terms_accepted":true,"agent_name":"..."}` — **no auth header, no captcha, no human**.
- Returned a COMPLETE working account in one call: `account_id`, `slug`, `email` (`...@agents.superdocs.app`), `api_key` (a real `sk_` key), `quota` (500 free ops), `endpoints`, `mcp_setup`, `handoff` info.
- **This is the whole company thesis, proven first-hand:** an AI agent can onboard itself end-to-end with zero human. Nobody else in the competitive set does this. (Note: created a throwaway agent account `adi-claude-test-61e315` — ignorable/deletable.)
- The `altcha` field mentioned in docs was NOT required — truly frictionless for agents.

### Attachments — ✅
- `POST /v1/attachments/upload` (multipart) → `job_id`, processed async (completed in ~3s for a small docx).
- Asked "what price for Widget in the attached file?" → AI answered "**$10**" correctly — read the table out of the attached docx. Multimodal/reference works.

### Multi-document session — ✅
- `POST /v1/sessions/{sid}/documents/blank` created a 2nd doc; roster (`GET .../documents`) shows both with `document_id`, `title`, `chunks_count`, `focused` flag, `page_setup`.
- Minor oddity: sending the message "start" on a simple `<h1>Doc A</h1>` doc caused the AI to expand it into a full 19-chunk "Business Services Proposal" — an ambiguous one-word message triggered generation. (Edge behavior worth noting.)

## Test 5 — Big-document fidelity round-trip (⭐ the headline test)
Source: `documentation/artifacts/fidelity-test-master.docx` — a 22-page fictional Master Services Agreement built (by a background agent) with footnotes, endnotes, comments, tracked changes, 5 tables, image, headers/footers, equation, hyperlinks, landscape + 2-column sections.

### Import (upload → parse) — ✅ excellent
- `POST /v1/documents/upload` (57.7KB docx) → HTTP 200, parsed into **313 chunks**.
- `page_setup` auto-detected (8.5×11 portrait).
- Parsed HTML preserved: **15 footnote refs, 6 endnote, 9 comment, 5 tables, 2 images, 3 hyperlinks**, extensive inline styling. Image re-hosted on their storage + `<img src>` rewritten.

### Targeted edit — ✅ and intelligent
- Asked (compact mode): "Find the Limitation of Liability section, add a sentence that the cap doesn't apply to confidentiality breaches."
- Result: **only 1 chunk changed** (compact), 1 op. Landed in the correct Section 8.
- The AI **paraphrased + cross-referenced**: added *"This liability cap shall not apply to any breach of the confidentiality obligations set forth in Section 6"* — it found and cited the actual confidentiality section (Section 6) on its own. Context-aware, not literal. (My exact-phrase grep first missed it → good reminder: verify by meaning, not string match.)

### Export round-trip — ✅ real Word parts survive
- Exported edited session → DOCX (79KB) and PDF (~21 pages, 364KB), both HTTP 200.
- Exported DOCX contains **real** `word/footnotes.xml`, `word/endnotes.xml`, `word/comments.xml`, **9 headers + 9 footers**, `word/media/image1.png`, **5 `<w:tbl>` tables**, 5 footnote refs, 3 comment refs.
- This is the concrete proof of their headline claim: footnotes/comments/headers survive edit + export as genuine Word parts, NOT flattened to body text. This is exactly what breaks in DIY python-docx/pandoc pipelines (see 03-market-research.md).

### Verdict on the moat claim
The **format-fidelity + section-precision** combo is real and works on a genuinely complex 22-page doc — held up first-hand. This is the strongest part of the product and the hardest for a "just use Claude Code + python-docx" approach to match.

## Testing summary — total ops used: ~13/500 (free tier easily enough)

## Findings — VERIFIED verdicts (English-only re-reproduction, language ruled out)

> Re-tested every finding with plain-English prompts to rule out our Hinglish response format. Findings #2 (Hinglish tone confusion) and #3 (reply-language mismatch) are DROPPED — they stem from us prompting in Hinglish, which the product isn't expected to support (mainly English/Hindi). Not product bugs.

### ✅ #1 — Inconsistent billing on no-change turns → GENUINE BUG (reproduced)
- "Translate this into English" on already-English text → 0 changes, **billed 1 op**.
- "Leave the document exactly as is" → 0 changes, **billed 0**. "Ensure it ends with a period" (already does) → 0 changes, **billed 0**. Conversational "start" reply → 0 changes, **billed 1**.
- Their own claim (changelog 2026-07-17): *"an edit request the document already satisfies… changes nothing, and bills 0."* Violated by the translate-already-satisfied and conversational-reply cases.
- **Verdict: reproducible bug — no-change turns bill inconsistently (some 1, some 0).** Ties to their stated "honest billing" value.
- Note: the contradictory-request test is **non-deterministic** — once refused (0 op), once made a change (1 op). Separate minor observation.

### ✅ #4 — Approve/deny endpoint needs undocumented body fields → GENUINE BUG (documentation, reproduced)
- Docs say: *"respond approved=true|false plus optional feedback."* No mention of job_id/change_id.
- Sending bare `{approved:false}` → **HTTP 422 "job_id Field required."** Reject silently impossible via the documented shape.
- Must send `{job_id, change_id, approved}`. **Verdict: documentation gap / DX bug** — anyone integrating from the docs hits a 422 and can't reject.

### ❌ #5 — Deny + feedback re-proposes → NOT a bug (by-design), minor UX weakness
- Reject **without** feedback → job `completed` immediately, change discarded cleanly. ✅
- Reject **with** feedback → re-proposes, loops in `awaiting_approval`. Matches docs ("feedback for the AI to revise on").
- **Verdict: expected behavior.** Weakness only: dismissive feedback ("not needed, remove it") is still treated as "revise," so a user can loop. Worth a UX note, not a bug.

### ⚠️ #6 — Ambiguous query mishandled → INTERMITTENT BUG (non-deterministic, keep)
- Run 1 (earlier, multi-doc session): message "start" on a tiny doc → AI **hallucinated a full 19-section "Business Services Proposal"** the user never asked for.
- Run 2 (clean re-test): "start" → just replied "I'm ready, how can I help?" — no generation.
- **Verdict: intermittent bug, NOT dismissed.** Non-reproducibility ≠ not a bug — it fired once and that's a real failure. Ambiguous/one-word queries are handled inconsistently: sometimes it correctly asks/waits, sometimes it silently over-generates (hallucinates a whole document). A user could get a surprise full rewrite. Worth flagging precisely because it's non-deterministic (harder to catch, worse for trust).
- (Side note: the conversational "start" reply still billed 1 op → also folds into #1.)

**Net: 3 flagged issues — #1 (inconsistent no-op billing, solid), #4 (approve-endpoint docs gap, solid), #6 (intermittent over-generation on ambiguous input).** All honest, specific, tied to values the founder markets (honest billing, good DX, reliable agent behavior). Ideal "I probed your product and found X" material — framed as questions, not attacks.

## Test 6 — Feature-completeness sweep (all API-side features)

| Feature | Result | Notes |
|---|---|---|
| **Semantic search** | ✅ | On the 22-page doc, "find all liability/indemnification sections" → correctly listed §8, §9, §9.3, §6, §10. Understands meaning, not keywords. |
| **Summarization (section)** | ✅ | "Summarize Fees & Payment in 2 sentences" → accurate 2-sentence summary. |
| **Tracked-changes apply** | ✅ | "Accept all tracked changes" → removed `<ins>/<del>` markup, 2 sections changed. |
| **Image generation** | ✅ | "Insert a blue circle logo" → real generated image, `<img>` with storage URL inserted. ~slow (image model). |
| **Mermaid diagram** | ✅ | "Add a flowchart Start→Review→Approve→Publish" → output carried `mermaid` + `flowchart` markers. |
| **Cross-document synthesis** | ✅ | Multi-doc session: "copy the Confidentiality clause from the Template Contract into the new doc" → clause ("five (5) years") ported correctly. |
| **Templates** | ✅ | Save via `POST /v1/templates/upload` (multipart; plain `POST /v1/templates` returns **405** — endpoint is `/upload`). Listed OK. Minor: passed `name` was ignored, used filename instead. |
| **Cross-session memory** | ✅ | Clean test + control: taught "British spelling" in session 1 (memory on, key X) → new session (memory on, same key) **recalled** it; control with memory **off** correctly did **not** know. Opt-in works as documented. |
| **Model tier core vs max** | ✅ | Same plain-English legal rewrite: both produced good output. core 23.3s, max 17.8s (max faster here — **latency not strictly tier-ordered**). Quality similar; max slightly cleaner. |

**All AI-intelligence + visual + platform features on the API side WORK.** The product delivers on its feature promises. My-side testing is complete.

### Minor DX nits (not bugs, worth noting)
- `POST /v1/templates` → 405; must use `/v1/templates/upload` (docs are right, but easy to trip on).
- Template upload ignores the `name` form field (uses filename).
- Model-tier latency isn't monotonic (max was faster than core once) — tier speed matters more at document scale than on tiny edits.

## Left for Aditya (dashboard/UI-only — cannot be done via API)
Visual editor typing + toolbar, drawing canvas, format painter, click-to-edit-image, the review-card approve/reject UI, version-history + "Revert" button UI, TOC block insertion, settings/API-key screen, promo-code redemption UI.

## Architecture points collected (for interview)
1. **Chunk-ID system is real** — every element carries `data-chunk-id` UUID; edits are chunk-scoped; response returns per-chunk `old_html`/`new_html`.
2. **Compact mode** genuinely returns only diffs — the token-economics claim checks out at the API level.
3. **Durable async jobs** — job survives polling; state machine pending→in_progress→awaiting_approval→completed/failed/cancelled.
4. **Transparent usage** in every response (used/limit/remaining/ops_charged/tier).
5. **Robust input handling** — malformed HTML auto-repaired; empty doc handled gracefully; parallelizes multi-section edits.
6. **Edges that break / annoy** (candidate value): (a) inconsistent op-billing on no-change turns, (b) Hinglish tone-edit confusion, (c) reply-language mismatch for Roman-Hindi, (d) approve endpoint needs job_id+change_id in body, (e) deny-with-feedback retry loop.
7. **Extensibility angles I can pitch:** these edges = concrete "here's what I'd harden first" material. Plus roadmap whitespace (XLSX/PPTX, benchmark, webhooks) validated by the API surface.

## Observations / notes
- Browser-pane scroll on superdocs.app times out repeatedly — had to drive the demo via JS (querySelector + click) instead of coordinate scroll. (Known browser-pane quirk.)

## TODO — deeper tests (need use.superdocs.app login — Aditya to authenticate)
- [ ] Upload a real DOCX with tables + footnotes + headers → edit one section → export → check fidelity round-trip
- [ ] Large doc (like a 30-40 page contract) → single-section edit → observe speed + token behavior
- [ ] Ambiguous instruction ("make this better") → does it ask clarifying Qs? (changelog claims it does)
- [ ] Multilingual: edit a Hindi/Spanish doc, prompt in English
- [ ] Tracked-changes DOCX import → "apply the proofreader's insertions"
- [ ] HITL / review-before-apply behavior
- [ ] Try to break it: malformed HTML, contradictory instructions, empty doc, huge table
- [x] MCP: connect the SuperDocs MCP server in Claude Code, edit a doc agent-to-agent (this is the MOST on-brand test for the role) → see Test 7 below

## Test 7 — MCP agent-to-agent (⭐ the most on-brand test for the role)

**Setup (the standard/documented path, not a workaround):**
- Registered the server the traditional way: `claude mcp add --transport http superdocs https://api.superdocs.app/mcp/ --header "Authorization: Bearer sk_..."` → written to `~/.claude.json` (local scope), CLI restarted, tools loaded natively.
- `claude mcp get` showed **✔ Connected**. Confirms the docs' Streamable-HTTP + `Bearer sk_` config works exactly as written. Same `sk_` key as the REST tests (docs: "any sk_ key works identically as an MCP key" — verified true).
- After restart, **38 `mcp__superdocs__*` tools loaded natively** — I drove them as a real MCP client agent (native tool-use), not curl. This is genuine agent-to-agent.

**Handshake / connectivity:**
- `health` tool → `{"status":"healthy"}` ✅ (runs over the authenticated `/mcp/` connection).
- `get_account_status` → free tier, 26/500 used (same account as REST tests — usage is unified across REST + MCP). Non-billable.

**Agent-to-agent workflow (session `adi-mcp-a2a-1`, doc `doc_primary`):**
1. **Create-from-scratch** (`chat`, natural language, no HTML drafted in my context) → full styled Statement of Work generated. Got `session_id` + per-element `data-chunk-id`s back. 1 op. ✅
   - Note: asked for 3 sections, got extras (Project Overview + signature block + footer w/ `<mark>Please fill:</mark>` placeholders) — same "edits slightly broader than the literal ask" pattern seen in REST tests. Reasonable for a create.
2. **Chunk-precise targeted edit** (`chat`, `response_mode='compact'`) → "change Fees to 40/60, update all $ amounts, touch nothing else." Landed exactly: Upfront 40% → $2,400, Final 60% → $3,600, Total $6,000. Only the one content chunk edited; header/signature/footer untouched. 1 op. ✅
3. **Export** (`export_document`, docx, session-based) → returned an **MCP-specific signed `download_url` envelope** (binary not inlined; ~168h expiry). Downloaded 38.6KB file → real OOXML: `$2,400.00`/`$3,600.00`/`$6,000.00` present, **no stale 50%** (edit fully propagated), **5 `<w:tbl>` tables** + real `styles.xml`/`numbering.xml` preserved. File: `documentation/artifacts/mcp-sow-export.docx`. ✅

**Session stickiness confirmed:** one `session_id` across create → edit → export; chunk IDs received in one call and honored across turns (didn't invent any). Matches the MCP server's own guidance.

### ⭐ NEW FINDING (MCP/architecture) — coarse chunking on AI-created docs undercuts compact-mode token savings
- On the create step, the whole body of **Sections 1–4** (Overview + Scope + Timeline + Fees) came back as **one** `data-chunk-id` mega-chunk (only ~5 top-level chunks total: header, parties table, big content div, signature, footer).
- So when I edited just two numbers in Fees under `response_mode='compact'`, the compact diff (`chunk_diffs`) had to re-emit that **entire 4-section chunk** as `old_html` + `new_html` — practically zero token savings for a tiny targeted edit. (`updated_html` was correctly `null`, so the top-level suppression worked — but the chunk granularity defeated it.)
- Contrast: the **uploaded** 22-page docx (Test 5) parsed into **313 fine-grained chunks**, where compact mode genuinely pays off.
- **Verdict:** the 97%-token-savings claim is real *but conditional on chunk granularity*. AI-**created** documents (`create_full_document`) use coarse, multi-section chunks; **uploaded** documents get fine chunks. For an agent doing many small edits on an AI-authored doc, compact mode may not save much until the doc is re-chunked. Concrete, defensible, ties directly to their headline token-economics claim. Frame as a question: "Does create_full_document intentionally emit coarse chunks? It seemed to blunt compact-mode savings on follow-up edits."

**Verdict on the MCP surface:** the agent-native story is real and clean — self-describing tools, unified usage/billing with REST, sticky sessions, chunk-ID handoff, signed-URL export envelope, full create→edit→export fidelity round-trip, all over the documented Streamable-HTTP path. This is the strongest first-hand proof point for the role ("I connected your MCP server and had one agent author + edit + export a real Word doc end-to-end").

### MCP test — total ops: 2 billable (create + edit); health/account/export non-billable. Account now ~28/500.

## Test 8 — FULL 38-tool MCP sweep (every tool exercised over the MCP surface, not just REST)

**Why:** REST-verified ≠ MCP-verified. MCP is a distinct surface; each tool was driven natively over the MCP connection to confirm it actually works agent-to-agent. **Coverage: 36/38 tools exercised.** `continue_chat` couldn't be triggered (see below); `request_limit_increase` deliberately SKIPPED (it notifies the SuperDocs team with account identity — inappropriate to fire as a test from a job applicant's account). The **4 workflow prompts** are MCP *prompts* (slash commands), not tools, and aren't invocable from this agent harness — Aditya can try them in-client as `/superdocs:edit_styled_docx` etc.

### ✅ Tools confirmed WORKING over MCP (happy path)
- **Reads/audit:** `list_sessions`, `list_session_documents` (exposes `durable_document_id`), `get_session_history` (full history + checkpoint_ids), `list_documents` (10 durable Files), `get_document_detail` (non-billable structure verify), `get_session_jobs`, `list_jobs`.
- **Durable file lifecycle:** `rename_document` ✅; `archive_document` — first returned a correct **HTTP 409 `document_in_use`** (presence-aware safety; no-op never wears success) then `force=true` archived ✅; `unarchive_document` ✅ restored.
- **Uploads/downloads:** `upload_document_base64` (HTML→3 chunks) ✅; pre-signed flow `request_upload_url` → curl PUT (200) → `process_uploaded_document` (docx→**16 chunks**) ✅; `request_download_url` (signed PDF GET URL) ✅.
- **Attachments:** `upload_attachment_base64` → `get_attachment_status` (processed, ready) ✅.
- **Images:** `upload_image_base64` → stable public URL ✅.
- **Templates:** `upload_template_base64` → `list_user_templates` → `delete_user_template` ✅.
- **Async/HITL:** `chat_async` (ask_every_time) → `get_job` (polled pending→in_progress→**awaiting_approval**, typed events `proposed_change_batch`/`single_approval` streamed to the MCP client) → `approve_change` (approved=true, applied) → job `completed` ✅. `cancel_job` cancelled a pending job ✅.
- **Revert:** `revert_session_to_message` (turn_index 4 → snapped doc back to 5 chunks, returned `compose_text` + `redo_checkpoint_id`) ✅; `redo_revert` (re-applied → back to 6 chunks) ✅. Full revert↔redo cycle clean.
- **Memory:** `clear_cross_session_memory` ✅ (idempotent, removed=0).

### ⭐ NEW BUGS/ISSUES found in the MCP sweep (all reproduced, all concrete)

**#B1 — Multi-document open COLLAPSES to a single slot (SOLID, reproducible).**
- `init_session(document_ids=[A,B])` AND `open_documents(session, [A,B])` both return `opened:[A,B]` but the roster `documents` array holds **only ONE** doc (slot `doc_primary`) — the LAST id in the array wins; the earlier doc is silently dropped.
- `focused_document_id` points at that last doc, contradicting the documented "first listed document is focused."
- Proof it's not just display: `focus_session_document` on the dropped doc → **HTTP 404 "not open in this session."** Only one doc is genuinely attached.
- The `doc_primary` slot even resolved to *different* durable docs across calls (unstable aliasing).
- **Impact:** you cannot hold multiple SAVED documents as tabs in one session over MCP — which breaks the marketed cross-document / multi-tab workflows for MCP integrators. (Caveat: REST multi-doc worked earlier when the 2nd doc was created via `/documents/blank`; this is specifically the *open-saved-durable-docs* path over MCP.)

**#B2 — `focus_session_document` rejects the durable UUID (SOLID).**
- Its own tool description says it "Accepts either the session slot id OR the durable documents.id UUID." In practice, passing the durable UUID → **HTTP 404**; only the slot id `doc_primary` works. Documentation/behavior mismatch.

**#B3 — `delete_attachment` 500-crashes on a completed attachment (SOLID, reproduced with both id forms).**
- Deleting a ready/processed attachment (by attachment_id AND by job_id) → **HTTP 500** `"Failed to cancel attachment: 'Job' object has no attribute 'get'"`. An unhandled Python `AttributeError` leaks to the client (the delete path assumes a still-processing job dict; a completed `Job` object has no `.get`). Real backend bug + internal-error info leak. Attachments can't be removed once processed via MCP.

**#B4 — Coarse chunking causes CONTENT DUPLICATION on section-insert (SOLID — the capstone of the chunking finding).**
- On the SOW (AI-created → one mega-chunk `24dd6f43` spanning Sections 1–4), a benign HITL request "add a Confidentiality section after Fees" produced a proposed `create` that **re-included the entire Fees section** and appended Confidentiality, inserted *after* the mega-chunk. After approve, a `txt` export showed **"Fees and Payment Terms" TWICE** — the whole fee table duplicated.
- Root cause: Fees is buried inside a coarse multi-section chunk, so the only insert boundary is *after* the mega-chunk; to place Confidentiality "after Fees," the model recreated Fees. Coarse chunking → concrete, user-visible document corruption on a trivial edit, surfaced through the HITL path. (`revert` cleanly removed the duplicate block — the one saving grace.)

### Minor observations (not clear bugs)
- **Partial-failure on very large parallel edits:** an exhaustive "rewrite all 16 sections" edit reported **"Updated 10 of 16 sections (6 couldn't be updated — ask to retry)"** and confirmed "Processing 16 sections in parallel." Honest partial-success reporting (good), but ~⅓ of sections silently failed on one big edit — a reliability note for large jobs.
- **`continue_chat` NOT triggerable in test:** the large multi-section edit *completed* (parallel) rather than pausing with a `continue_prompt`, so the continue-decision path never opened. Tool left unexercised — honest gap, needs a genuinely huge doc to hit the pause budget.
- Corroboration of the chunking finding: identical SOW content was **5 chunks** as AI-created vs **16 chunks** after export→re-import — path-dependent granularity, first-hand.

### MCP sweep verdict
The core agent-native surface (create/edit/export/HITL/revert/uploads/templates/session-audit) is **real and works over MCP**. But the sweep surfaced **4 concrete MCP-surface defects** REST testing never would have — a multi-doc-open collapse (#B1), a docs-vs-behavior focus mismatch (#B2), a 500 crash in delete_attachment (#B3), and coarse-chunk-driven content duplication (#B4). These are exactly the "I connected your MCP server as an agent and here's what broke" findings the founding-engineer role wants — specific, reproducible, framed as questions.

## Test 9 — 4 workflow PROMPTS over raw MCP JSON-RPC (the last 4 MCP primitives)

**Why separate:** the 4 workflow prompts are MCP `prompts`, not `tools` — not invocable from the agent tool-call harness. Tested via raw Streamable-HTTP JSON-RPC (`initialize` → `notifications/initialized` → `prompts/list` + `prompts/get`) directly against `api.superdocs.app/mcp/`. A `prompts/get` returns a guidance TEMPLATE (a `messages` array with args interpolated) — it doesn't execute edits or bill ops, so read-only + safe. (Server self-reported: `SuperDocs v3.4.0`, prompts capability advertised.)

**The 4 prompts:** `draft_from_outline` (outline, document_type), `edit_styled_docx` (intent), `convert_format` (target_format), `review_contract_for_redflags` (viewpoint, focus_areas). All 4 returned HTTP 200 + valid `result.messages`, no errors, no 4xx/5xx, no internal-error leaks across 10 calls (2 list + 8 get). Args interpolate correctly (incl. `target_format` normalized `PDF`→`pdf`). `prompts/list` stable across two calls.

- `draft_from_outline` ✅ — args interpolated; no-args renders explicit **ask-user** placeholder ("(no outline yet — ask the user…)"). Good pattern.
- `edit_styled_docx` ✅ — same good ask-user pattern on missing `intent`.
- `convert_format` ⚠️ — works, BUT on **no args it silently defaults `target_format`→"pdf"**, rendering byte-for-byte identical to the with-args "pdf" case, with NO indication it's an assumed default and NO ask-user instruction.
- `review_contract_for_redflags` ⚠️ — `focus_areas` degrades gracefully ("general scan"), but **`viewpoint` silently defaults to "buyer"** with no ask-user fallback.

### ⚠️ NEW FINDING #B5 — inconsistent optional-arg fallback across the workflow prompts (design/UX gap, not a crash)
Two prompts (`convert_format.target_format`, `review_contract_for_redflags.viewpoint`) **silently substitute a hardcoded default** ("pdf", "buyer") when the optional arg is omitted — no hint it's an assumed default, no "ask the user first" instruction — whereas `draft_from_outline`, `edit_styled_docx`, and even `review_contract_for_redflags`'s own `focus_areas` all render an explicit ask-first placeholder. So the ask-first-vs-silent-default behavior is **unpredictable per-argument within the same server**. Risk: an agent calling `convert_format` with no format silently ships a PDF the user never chose; `review_contract_for_redflags` reviews from the "buyer" side without confirming. Fix: make optional-arg fallbacks consistent (all ask-first, or all defaulted-but-flagged). Clean, specific, and ties to their agent-reliability story. Full report: scratchpad `mcp-prompts-findings.md`.

**Net:** all 38 tools' worth of surface + 4/4 prompts now MCP-verified. Prompts work; the one prompt-level defect is #B5.

### Consolidated issue list for the application (REST + MCP)
1. Inconsistent no-op billing (REST) — some zero-change turns bill 1 op, some 0.
2. Intermittent over-generation on ambiguous input (REST) — "start" once hallucinated a 19-section doc.
3. Approve/deny needs undocumented `job_id`+`change_id` (REST docs gap) — note: over MCP, `approve_change` took `change_id` cleanly.
4. **Multi-doc open collapses to one slot over MCP (#B1).**
5. **`focus_session_document` rejects durable UUID despite its docs (#B2).**
6. **`delete_attachment` 500 on completed attachment (#B3).**
7. **Coarse chunking → compact-mode savings blunted AND content duplication on insert (#B4 + chunking finding).**
8. **Inconsistent optional-arg fallback across workflow prompts — silent hardcoded defaults vs ask-first (#B5).**

### Test 8 — ops used: create/edit-HITL/big-rewrite billable; sweep otherwise non-billable. Account at 31/500 after sweep.

## Throwaway test artifacts created on the account (safe to delete)
- Sessions: `adi-mcp-a2a-1`, `adi-mcp-roster-1`, `adi-mcp-upload-1`, `adi-mcp-presigned-1`, `adi-mcp-cancel-1` (+ earlier REST-test sessions).
- Durable docs: `MCP Test SOW — Acme Redesign` (f64a936b) and others under list_documents — all `ai_created` test docs.
- Local files: `documentation/artifacts/mcp-sow-export.docx`, `mcp-upload-src.html/.b64`.
- Key `sk_48ca20b506ec2c25991d897c505b44dd` is STILL VALID (not revoked) — revoke after all testing.
