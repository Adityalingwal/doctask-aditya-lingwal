# doctask-aditya-lingwal

An agentic system that reads software requirements-to-delivery documents and
builds a grounded **Requirements-to-Delivery Register**. Each row traces one
client requirement through written scope and testing. Exact source evidence and
a human approval gate prevent unsupported rows from being exported.

## Current working scope

Slice 1, the formats and types slice, and the rules and findings slice are
implemented:

`Document folder → Ingest → Extract → Match → Examine → Review → Commit → JSON/Markdown export`

- PostgreSQL stores projects, runs, documents, register rows, citations,
  review decisions, findings, audit entries, and LangGraph checkpoints.
- FastAPI exposes six machine-drivable endpoints.
- A run returns immediately, continues in the app process, and is polled.
- Review decisions are one proposal at a time; export is unavailable until
  approved.
- Examine judges the whole register against the rules the run froze and raises
  a finding as a question, never as an edit.
- Startup resumes a run killed mid-flight from its durable checkpoint.
- Automated tests use a scripted model and no live API key.

No live hosted-model run has been completed yet. Current proof is for the
orchestration, persistence, validation, review, and export paths using the
scripted client.

## Rules and findings

`config/rules.yaml` holds the rules the register is judged against; R1–R4 ship
with the repository. Two further checks, D1 and D2, are owed by the deliverable
itself and live in code: every row cites a source, and no row is `Done` without
a testing outcome.

Examine runs once per run, between Match and Review, in a single model call for
the whole register. Each finding names its rule, the row it is about, what it
found, and the evidence — and becomes a question the Delivery Owner answers.
Approving one attaches it to the row; rejecting one keeps it in the run record
and out of the export. A finding never edits a cell, and attaching one does not
change the row's fingerprint, which covers the seven cells only.

A run with nothing wrong says so: `GET /runs/{id}` and both exports name the
rules that ran and how many rows they ran against, alongside an empty findings
list.

## Domain

**Software Requirements-to-Delivery** — documents created after a client
starts sharing software requirements, while a Software Provider clarifies,
builds/configures and delivers the work, and while the client tests it and
returns feedback or changes.

Pre-sales demos, pricing, contracts, invoices, payments, deployment, project
resourcing, and CRM work are outside this domain.

## Formats

| Format | Declared V1 set | Working now | Citation place |
|---|---:|---:|---|
| `.md` | Yes | **Yes** | Nearest heading |
| `.pdf` | Yes | **Yes** | Page number |
| `.docx` | Yes | **Yes** | Line number |
| `.txt` | Yes | **Yes** | Line number |
| `.xlsx`, `.pptx`, `.eml`, images | No | Skipped with reason | — |

`config/formats.yaml` declares which extensions are accepted and the document
page limit, currently 20 pages. A file whose extension is not listed there
never reaches a reader, and startup warns if the file names a format no reader
exists for.

A document is skipped, with its reason recorded on the run, when it is longer
than the page limit, when a PDF is encrypted, and when a PDF has no text layer
because it was scanned. The page limit applies to PDFs, the only declared
format that reports a page count.

## Run locally

Requirements: Docker with Docker Compose.

```bash
cp .env.example .env
```

Set a non-empty `POSTGRES_PASSWORD`. For a real run, also set
`OPENROUTER_API_KEY`; the service can start without it, but `POST /runs` reports
why runs are unavailable. Then start the app and database:

```bash
docker compose up --build
```

The API is at `http://localhost:8000`; `GET /health` returns
`{"status":"healthy"}`. Startup creates the synthetic **Acme intake portal**
project if it is missing. The generated API schema at `/docs` shows the six
operations:

- `POST /projects`
- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/decisions`
- `POST /runs/{id}/finish-review`
- `GET /runs/{id}/export?format=json|markdown`

The application currently reads project folders from inside the repository.
The included demo folder is `sample-projects/intake-portal`; a second synthetic
project in mixed formats is `sample-projects/northside-dental`.

The application listens on `127.0.0.1` only by default; to expose it beyond
this machine, change `APP_HOST` and the `app` service's `ports:` mapping in
`docker-compose.yml`.

## Test

```bash
docker compose run --rm app pytest
```

Last verified on the `rules-and-findings` branch: **93 passed**, real
PostgreSQL, no live model key. Fresh-clone and image-only verification remain
open release checks; this is a verified development-worktree command, not yet
a fresh-machine claim.

## Configuration

| File | Purpose |
|---|---|
| `config/formats.yaml` | Declared extensions and document page limit |
| `config/model.yaml` | OpenRouter model, endpoint, rates, attempts, timeout |
| `config/rules.yaml` | User-editable R1–R4 rule set Examine judges against |

Adding or changing a rule is an edit to `config/rules.yaml`, never a code
change. A run freezes the parsed rules when it starts, so an edit applies to
the next run and never to one already under way or already finished. Point
`RULES_CONFIG_PATH` at another file to use your own rule set. See
[`config/README.md`](config/README.md).

## Current limitations

- The 20-page limit applies to PDFs only; the other formats report no page
  count and none is invented for them.
- Scanned PDFs are skipped rather than read; there is no OCR.
- A related additional document that lists requirements, in a run that never
  exports, is read again by the next run.
- The durable per-project lock and waiting queue are built, but dedicated
  concurrency tests are pending.
- A kill after a model response but before its checkpoint can repeat that one
  paid call; earlier completed calls and register rows do not duplicate.
- A run waiting for Review holds the project lock; later files wait.
- Watched-folder auto-start, MCP, React, focused incremental updates,
  unchanged-row proof, and cost/timing reporting are later slices.
- A rejected finding will not automatically return if later evidence makes it
  stronger, and a finding already approved onto a row is not re-examined by a
  later run.
- The development Compose file bind-mounts the worktree, which exposes local
  `.env` and lets local files override the image; this is retained for
  iteration and is not yet removed for final image-only verification.

## Project truth

- [`DECISIONS.md`](DECISIONS.md) — compact current decisions and limitations.
- [`PROGRESS.md`](PROGRESS.md) — current status, blockers, and next actions.
- [`documentation/decision-history.md`](documentation/decision-history.md) —
  detailed append-only decision history.
- [`documentation/progress-history.md`](documentation/progress-history.md) —
  completed progress narrative.
- `documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`
  — interpreted brief requirements, separate from our decisions.
