# sample-documents/helpline-ai

A made-up client project for the demo: **BrightCart**, an e-commerce company,
has hired a software provider to build an AI customer-support product. The
four documents carry seven requirements: voice agent, chat widget, WhatsApp
support, transcripts dashboard, human escalation, weekly analytics report,
and Hindi/English support.

| File | What it is |
|---|---|
| `meeting-notes-02-jul.md` | First call. Mentions all seven asks — human escalation only verbally |
| `client-requirements-v1.md` | Written scope. Six of the seven — human escalation left out |
| `handover-summary.md` | Delivery note. Four things delivered, call transcripts unfinished |
| `testing-feedback-12-aug.md` | Client's testing. Two passes, two missing, one defect, one new ask (an SMS follow-up) |

## Expected end state

Read all four in that order and the register ends like this (the outcome of
a real model run — wording varies between runs, the cells below do not):

| Row | Status | Written down | What testing found |
|---|---|---|---|
| Voice agent | Done | Yes | testing passed |
| Chat widget | Done | Yes | testing passed — the SMS ask is a change request and moves nothing |
| WhatsApp support | Not delivered | Yes | reported absent, no handover claim behind it |
| Transcripts dashboard | Partial | Yes | defect on delivered work |
| Human escalation | Disputed | Not mentioned | handover says built, testing says absent |
| Weekly analytics report | Handed over | Yes | Not mentioned |
| Hindi and English | Requested | Yes | Not mentioned |

Three findings are also expected on this register:

- Weekly analytics report — written down, but no testing outcome.
- Hindi and English — written down, but no testing outcome.
- Human escalation — built, but never written down.

None of these documents tries to give the system instructions; that
protection is proved by the tests, not by this corpus.

## Running it

See the root README's "Run it" — copy the documents into
`sample-projects/helpline-ai/` one at a time. That folder is git-ignored.
