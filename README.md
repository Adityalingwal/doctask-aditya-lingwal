# doctask-aditya-lingwal

## What this system does

An agentic system that reads a pile of software-feature-delivery documents
and produces a register — one row for each customer request, tracing what
was asked, what happened to it, and where the documents disagree. A human
approves every row before anything commits.

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

**Software feature delivery** — the documents a development team and its
customer produce while a feature is requested, built, tested, and changed.