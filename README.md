# doctask-aditya-lingwal

## What this system does

An agentic system that reads documents from a software requirements-to-delivery
workflow and produces a grounded **Requirements-to-Delivery Register**. Each
row traces one client requirement through delivery and testing, with gaps,
blockers, conflicting evidence, and rule findings surfaced for human review
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

## Limitations

- **A rejected finding does not come back on its own, even if it later gets
  stronger.** Once the Delivery Owner rejects a finding, it stays out of the
  register for good — this is what makes "do not ask again" possible. The
  common case is safe: new evidence that *resolves* the problem simply stops
  the rule from breaking, so no finding is produced at all. Only the rarer
  case — new evidence that makes an already-rejected finding truer — stays
  silently suppressed in V1.

- **R3 cannot fire on time.** The rule "no requirement stays blocked beyond
  `max_days`" turns on elapsed time, but a run only starts when a document
  arrives. A blocker passing its threshold during a quiet spell raises
  nothing until the next document lands — late, not lost.

- **One run at a time per project.** A second run queues rather than
  failing. A run parked at human review holds that place for as long as the
  reviewer takes, so a queued run may wait a long time — it is waiting, not
  stuck.

- **Documents beyond the configured page limit are skipped**, with the
  reason given, rather than being split up.

## Assumptions

- **Who starts a run.** The brief does not say. Our call: the system watches
  the location and reports what has arrived, but a run itself is
  started by the Delivery Owner, or by a machine calling the same operation.
  Reason: auto-starting would break the one-run-one-batch rule and is the
  easiest route into the duplicate-run problem the brief grades.
