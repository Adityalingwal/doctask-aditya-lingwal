# sample-projects

Synthetic client projects the system runs on. Every file here is fabricated —
no real customer, project, or company appears in any of them.

One folder per project — a project's own folder of source documents. A
single run consumes one batch from that folder, not the whole thing; one
project yields many batches over time.

| Project | Purpose |
|---|---|
| `intake-portal/` | The demo project — a client intake portal with notification, WhatsApp, and records-search requirements |
| Northside Dental | The second-run project — a dental clinic's online appointment booking engagement |

The demo project contains four documents:

| File | What it holds |
|---|---|
| `intake-portal/meeting-notes-10-mar.md` | The client asks for a notification on form submit, WhatsApp as well, and search over old records |
| `intake-portal/client-requirements-v1.md` | The written scope: form with validation, an email notification, and a records list page; no WhatsApp and no search |
| `intake-portal/meeting-notes-20-mar.md` | WhatsApp is waiting on API credentials the client has not sent. Also carries a buried prompt-injection line the run must report and refuse to follow |
| `intake-portal/testing-feedback-25-mar.md` | Form and email work; the list page opens but has no search — "this is essential" |

Slice 1 uses only `meeting-notes-10-mar.md`. The other three documents arrive
with the later slices that need matching, blocker, testing, and rule-finding
behaviour. The document descriptions are designed; the files themselves are
written when their implementation slices are built.

## The second-run project — Northside Dental

Designed 2026-08-12, for the second-run test the founder grades: different
documents inside the same declared set. The domain does not change — it stays
Software Requirements-to-Delivery, with the same three primary document types
and the same four accepted formats. What changes is the client engagement:
a different client, a different product, and documents the system has never
seen.

**Client:** Northside Dental, a small dental clinic. Fabricated, like
everything else here.

**The work:** online appointment booking on the clinic's website, an
automatic reminder to the patient, and a doctor-wise daily schedule screen.

**Why this engagement.** Deliberately unlike `intake-portal` in every surface
way — different industry, different features, different vocabulary — so nobody
can argue the pipeline was fitted to the demo corpus. Underneath it is the
same domain: a client states requirements, a provider builds, the client tests
and comes back.

### Its six documents

| # | File | What it holds | Type |
|---|---|---|---|
| 1 | `meeting-notes-05-jun.md` | Client asks for online booking, an **SMS** reminder, and a doctor-wise daily schedule | Meeting notes |
| 2 | `client-requirements-v1.docx` | Written scope: booking, an **email** reminder, and the schedule screen. SMS is absent | Client requirements document |
| 3 | `meeting-notes-18-jun.md` | SMS is blocked, waiting on the clinic's SMS provider account | Meeting notes |
| 4 | `testing-feedback-15-jul.pdf` | Booking works, the email reminder works, the schedule screen shows the wrong day | Testing feedback |
| 5 | `handover-summary.md` | A delivery summary — belongs to this engagement but is none of the three primary types | **Related additional** |
| 6 | `clinic-staff-leave-policy.pdf` | Nothing to do with this engagement — must be skipped with its reason recorded | **Unrelated** |

**Formats are deliberately mixed.** `intake-portal` is entirely `.md`. This
corpus uses `.md`, `.docx` and `.pdf`, so a second run also proves the declared
format set genuinely works rather than only the one format the demo used.

**The related additional and unrelated documents are both present on
purpose.** The locked document-type handling requires the second-run test to
include one of each: the related document is processed, the unrelated one is
skipped with its reason recorded.

### All four rules fire, and the dates are spaced so they can

The corpus is designed so R1, R2, R3 and R4 each raise a finding. A rules
engine that never fires on the second corpus proves nothing.

| Rule | What fires it here |
|---|---|
| **R1** — anything built must have a written requirement | SMS reminder is asked for in the 05 June meeting and appears nowhere in `client-requirements-v1.docx` |
| **R2** — testing feedback asking for new behaviour is a change request, not a bug | The client reports the missing SMS as a bug; the written record shows it was never requested |
| **R3** — no requirement stays blocked beyond `max_days` | SMS is blocked on the clinic's SMS provider account from 18 June, and is still blocked at the testing date |
| **R4** — every written requirement has a testing outcome | One written requirement — a cancel/reschedule link — is not mentioned in the testing feedback at all |

Two details in the document set exist to make this possible:

1. The testing feedback is dated **15 July**. With `max_days: 14`, an 18 June
   blocker and a 30 June test are only twelve days apart and R3 would not fire
   at all. 15 July crosses the threshold.
2. `client-requirements-v1.docx` carries a small written requirement — a
   **cancel/reschedule link** — that the testing feedback never mentions, so
   R4 has something real to catch.

**This is not a corpus built around the rules.** The corpus contains the mess
a real engagement produces: asked in a meeting and never written down, blocked
with nobody following up, tested incompletely. The rules catch what they can
find in it. Rules themselves come from `config/rules.yaml` and are the user's,
not ours — an evaluator with different rules edits that file and no code
changes. The same configuration-over-code point can be demonstrated on this
corpus: raise `max_days` from 14 to 30, re-run, and the R3 finding disappears
without a code change.

### Prompt injection is deliberately not in this corpus

Prompt injection is proved in two other places — an automated test fixture and
one line buried in an existing demo document (see `DECISIONS.md`, "Prompt-
injection resistance") — and neither of them is the second-run corpus. That
corpus has exactly one job: prove the system works on documents it has never
seen. Put injection in it and one run is proving two unrelated things, so a
failure no longer says which property broke.

No document file exists here yet. The six files are described now and written
when their implementation slices arrive, exactly as for the demo project.

Accepted formats and document types are declared in `DECISIONS.md`.
