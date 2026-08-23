# sample-documents/helpline-ai

The corpus for **Helpline AI**, a fabricated client engagement: the client is
**BrightCart**, a mid-size e-commerce company; the Software Provider is
building an AI customer-support product for them. This is the input for the
first live-model run — it is staged into a project folder by hand, in
stages, and is never driven through the pipeline by an automated test.

Seven requirements come out of these documents, at the granularity the
client actually gave them: voice agent, chat widget, WhatsApp support,
transcripts dashboard, human escalation, weekly analytics report, and
Hindi/English support.

## The four documents

| File | What it holds |
|---|---|
| `meeting-notes-02-jul.md` | First call, 2 July 2026. Mentions all seven requirements conversationally, including human escalation — raised verbally, as an aside, and never written down after this |
| `client-requirements-v1.md` | Written scope, 5 July 2026. Lists six of the seven; human escalation is deliberately absent |
| `handover-summary.md` | Delivery note, 5 August 2026. Voice agent, chat widget, human escalation and the weekly report are reported delivered; call transcripts are not ready yet; WhatsApp and Hindi/English are not mentioned at all |
| `testing-feedback-12-aug.md` | BrightCart's testing round, 12 August 2026. Voice agent passes; the chat widget passes but carries a bug-phrased new ask for an SMS follow-up; WhatsApp is reported absent; call transcripts are reported missing; human escalation is reported absent (not merely buggy); the weekly report and Hindi/English are not mentioned |

## Expected end state — the outcome of the live-key run, not an acceptance check for this corpus

| Row | Status | Why |
|---|---|---|
| Voice agent | Done | testing passed |
| Chat widget | Done | testing passed (the SMS ask is a change request and moves nothing) |
| WhatsApp support | Not delivered | testing reports it absent, no handover claim behind it |
| Transcripts dashboard | Partial | defect on delivered work |
| Human escalation | Disputed | handover says built, testing says absent |
| Weekly analytics report | Handed over | delivered, testing silent |
| Hindi and English | Requested | written down, no delivery or testing evidence |

## Which rule each hook feeds

- **The written-requirement rule (R1)** — human escalation is built
  (`handover-summary.md`) but was only ever asked for verbally
  (`meeting-notes-02-jul.md`), never in `client-requirements-v1.md`.
- **The change-request rule (R2)** — the SMS follow-up is testing feedback
  asking for new behaviour, logged as a bug, with no written requirement
  behind it.
- **The testing-outcome rule (R4)** — Hindi/English and the weekly analytics
  report are both written down and never mentioned in the testing feedback.
- **The fourth rule (R5, no row `Done` without a testing outcome)** is
  expected to find nothing here, by design: `status_after`
  (`app/register/move_rows.py`) only produces `Done` from a testing pass, so
  a corpus honestly built this way cannot make it fire. This corpus does not
  try to.

This corpus carries no prompt injection. That behaviour is proved by the
fixtures in `tests/`, deliberately not by this corpus.

## Staging it for a run

The documents are never placed inside `sample-projects/` in this repository;
they are copied in by hand, one batch at a time, so the watcher fires once
per batch rather than once over a whole dump:

```bash
mkdir sample-projects/helpline-ai        # empty folder, create the project on it
# then copy documents in one at a time (or in pairs), waiting for each run:
cp sample-documents/helpline-ai/meeting-notes-02-jul.md sample-projects/helpline-ai/
# ... watcher: poll_seconds 4, quiet_seconds 10
```

Create the project first, through the screen's Add-project box or the MCP
`create_project` tool, over the empty `sample-projects/helpline-ai` folder.
`sample-projects/helpline-ai/` is git-ignored, so staged copies never dirty
the tree.
