# sample-projects

Synthetic client projects the system runs on. Every file here is fabricated —
no real customer, project, or company appears in any of them.

One folder per project — a project's own folder of source documents. A
single run consumes one batch from that folder, not the whole thing; one
project yields many batches over time.

| Project | Purpose |
|---|---|
| `intake-portal/` | The demo project — a client intake portal with notification, WhatsApp, and records-search requirements |

The demo project contains four documents:

| File | What it holds |
|---|---|
| `intake-portal/meeting-notes-10-mar.md` | The client asks for a notification on form submit, WhatsApp as well, and search over old records |
| `intake-portal/client-requirements-v1.md` | The written scope: form with validation, an email notification, and a records list page; no WhatsApp and no search |
| `intake-portal/meeting-notes-20-mar.md` | WhatsApp is waiting on API credentials the client has not sent |
| `intake-portal/testing-feedback-25-mar.md` | Form and email work; the list page opens but has no search — "this is essential" |

Slice 1 uses only `meeting-notes-10-mar.md`. The other three documents arrive
with the later slices that need matching, blocker, testing, and rule-finding
behaviour. The document descriptions are designed; the files themselves are
written when their implementation slices are built.

The second-run project is still to be designed. It will use a different
engagement inside the same declared set and must include one related additional
document and one unrelated document.

Accepted formats and document types are declared in `DECISIONS.md`.
