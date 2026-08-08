# SuperDocs — Product Deep-Dive Notes (for job application)

## One-liner
AI document editing platform — AI sits INSIDE the document (not a sidebar chat). Send doc + natural-language instruction → AI edits only the targeted section, formatting preserved.

## 4 usage modes (their own framing)
1. Manual editing (you) — web editor at use.superdocs.app
2. You + AI — chat-driven editing in web app
3. Your Product + AI (your users) — REST API / white-label embed
4. AI Autonomously (your AI) — MCP server / API, no human in loop

## Core architecture (under the hood)
- Documents parsed into structured HTML; every paragraph/heading/table/row/cell gets a `data-chunk-id`
- AI targets specific chunks → edits only that section → returns `chunk_diffs` (compact mode) instead of whole doc
- This is the 97% token saving: doc processed once, structure remembered per session; single-section edit returns ~500-2K tokens vs ~130K for a 100-page doc
- Session = caller-chosen `session_id`; full doc state + conversation + attachments + HITL state persist in DB, survive restarts/autoscaling
- Multi-step autonomous reasoning: plan → search sections (semantic) → edit → verify; automatic error recovery with fallback strategies
- SSE streaming: intermediate, proposed_change_batch (HITL diffs), document_sync, continue_prompt, documents_changed, model_fallback, final, usage, error; sequence numbers + replay on reconnect
- 4 model tiers (core/turbo/pro/max) × 3 thinking depths (fast/balanced/deep) — all on every plan
- Pre-signed upload/download URLs for >100KB files — bytes never enter agent context
- Stack (from job post): Python+FastAPI, LangGraph-class orchestration, React+TS+TipTap, PostgreSQL+pgvector, GCP Cloud Run/Cloud SQL, Docker

## Feature groups
1. **Core editing**: section-precision edits, style preservation (tables/fonts/colors round-trip to docx/pdf)
2. **Doc intelligence**: semantic search in doc + across attachments, summarize section/whole doc, cross-document synthesis ("port indemnity clause from other contract")
3. **Rich formatting**: full toolbar via NL, tables cell-level ops, headers/footers/footnotes/endnotes/comments as first-class editable parts (chat-editable, HITL-reviewable, export as real Word parts)
4. **Visual media**: image gen (auto model pick), NL image editing, Mermaid diagrams (re-editable as code), drawing canvas, KaTeX equations (export as native Word math), auto-TOC
5. **Knowledge**: attachments (PDF/DOCX/images, multimodal vision), knowledge base from attachments, semantic indexing
6. **Import fidelity**: PDF annotations + embedded images preserved, scanned PDF OCR, multi-column layout, Word track-changes import (AI can "apply proofreader's insertions"), legacy .doc/.odt/.rtf
7. **Control**: HITL approval mode (batched proposed_change_batch, approve/deny/feedback per change, atomic apply, denied = not billed), per-message revert (chat + doc rewind together, branch kept server-side), redo_revert
8. **Multi-doc & persistence**: multi-document sessions (tabs, focus, open_mode), durable Files library, cross-session memory & search (opt-in, off by default, per-end-customer scoping for B2B), concurrent editing conflict resolution (per-chunk re-edit endpoint)
9. **Ops**: async jobs w/ job_id polling, 30-min turn cap, per-org feature flags, promo codes, usage in every response, org API keys (lce_) vs user keys (sk_)

## Agent-first design (the big bet)
- `POST /v1/agents/signup` — AI agent creates its OWN account in one call, gets API key + 500 free ops; human can adopt account later (agent handoff/adopt endpoints)
- llms-full.txt — entire docs in one AI-optimized file
- Agent Editing Playbook + Agent Tool Integration guides (how to wire SuperDocs as a tool in your own agent loop)
- MCP server: 38 tools + 4 workflow prompts at api.superdocs.app/mcp/, Streamable HTTP, OAuth RFC 9728
- "A note to AI agents" in job post itself — consistent brand thread

## Pricing
- Free: 500 ops/mo, full features, no card
- Plus $20: 2,000 ops, capped overage
- Pro $99: 10,000 ops, uncapped overage
- Enterprise: white-label, custom deploy (dedicated/on-prem roadmap), BYO LLM, SLA
- Operation = 1 AI request; large edits = 1 op per 25 sections; denied HITL changes not billed
- Differentiation by VOLUME not features (every plan has full editor+API+MCP)

## Ship velocity (from changelog — interview gold)
- Weekly-to-daily meaningful releases Apr→Jul 2026
- Apr 19: large-doc edit latency 4m55s → ~10s
- Honest engineering: "honest no-op replies" (already-satisfied edit = 0 billed), model_fallback event, export warnings header, structured 413 errors
- Roadmap: branch switcher, EU residency, SOC2, on-prem, Word add-in, editor SDK, benchmark (SWE-bench for docs), own fine-tuned models

## Gaps / improvement ideas (for form + task + interview)
1. Real-time collaboration (multi-user cursors, Google-Docs-style) — only concurrent-edit conflict resolution exists
2. No native spreadsheet/slides support (docs only) — PPTX/XLSX editing is an obvious expansion
3. No JS/Python SDK (deliberate "no SDK" positioning, but typed SDK via Stainless would lower friction)
4. Diff view between arbitrary versions (has revert, but no visual version-compare UI)
5. Templates marketplace / community library
6. Grammarly-style passive suggestions (currently only command-driven)
7. Benchmark doesn't exist yet — they plan it; strong candidate contribution
8. Webhooks (polling-only for async jobs today, it seems)
9. Batch API endpoint for bulk doc processing (currently loop-your-own)
10. Word/Google-Docs add-ins — on roadmap, not shipped

## Competitors (initial map — deep-dive pending)
- **In-doc AI incumbents**: Microsoft Copilot in Word, Google Gemini in Docs, Notion AI, Grammarly — bundled, not API-first, weak on white-label/agent use
- **Editor-SDK + AI**: TipTap AI (Content AI), CKEditor AI Assistant — frontend-first, need your own LLM keys; SuperDocs is backend-first, editor-agnostic
- **Doc-gen APIs**: PandaDoc, Docupilot, Anvil, Carbone — template-fill, not conversational editing
- **AI writing apps**: Type.com, Lex.page, Jasper, Writer — human-facing, not agent-facing
- **Name clash**: superdoc.dev — open-source DOCX editor (different product!) — worth knowing to avoid confusion
- SuperDocs' wedge: agent-native (MCP + agent signup) + section-precision token economics + format fidelity round-trip. Nobody else combines all three.

## Brownie points for the form
- Actually used the product (mandatory per job post) — TODO: do a real edit session on use.superdocs.app
- Reference specifics: chunk-ID architecture, compact mode token math, agent self-signup, honest no-op billing
- Their pre-announced question: "agents doing work of 20-100 people while humans steer" — prepare answer using loop-engineering framing
- Disclose AI-assisted application (counts in favor per the post)
