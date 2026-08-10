# doctask-aditya-lingwal

## What this system does

An agentic system that reads documents from a software requirements-to-delivery
workflow, traces what a client requested and what happened during delivery and
testing, and surfaces gaps, blockers, and conflicting evidence for human review
before anything commits.

## Document formats accepted

| Format | Supported? | Notes |
|---|---|---|
| `.pdf` | ✅ | Text-based PDFs only. Scanned, encrypted, and image-based PDFs are skipped with reason. |
| `.docx` | ✅ | Standard Word documents. |
| `.md` | ✅ | Markdown files. |
| `.txt` | ✅ | Plain text files. |
| `.xlsx`, `.pptx`, `.eml`, images | ❌ | Skipped — `unsupported format`. |

**PDF limitations:** Tables are extracted with structure preserved. Multi-column
layouts are best-effort — some column ordering may be garbled.

## Domain

**Software Requirements-to-Delivery** — the documents created after a client
starts sharing software requirements, while a software provider clarifies,
builds or configures and delivers the work, and while the client tests it and
returns feedback or changes.

Pre-sales demos, pricing, contracts, invoices, and payment records are outside
this domain.
