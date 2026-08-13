# doctask-aditya-lingwal

An agentic system that reads software requirements-to-delivery documents and
builds a grounded **Requirements-to-Delivery Register**. Each row traces one
client requirement through written scope and testing. Exact source evidence and
a human approval gate prevent unsupported rows from being exported.

## Current working scope

Slice 1 is implemented:

`Markdown folder → Ingest → Extract → Match → Review → Commit → JSON/Markdown export`

- PostgreSQL stores projects, runs, documents, register rows, citations,
  review decisions, audit entries, and LangGraph checkpoints.
- FastAPI exposes six machine-drivable endpoints.
- A run returns immediately, continues in the app process, and is polled.
- Review decisions are item-by-item; export is unavailable until approved.
- Startup resumes a run killed mid-flight from its durable checkpoint.
- Automated tests use a scripted model and no live API key.

No live hosted-model run has been completed yet. Current proof is for the
orchestration, persistence, validation, review, and export paths using the
scripted client.

## Domain

**Software Requirements-to-Delivery** — documents created after a client
starts sharing software requirements, while a Software Provider clarifies,
builds/configures and delivers the work, and while the client tests it and
returns feedback or changes.

Pre-sales demos, pricing, contracts, invoices, payments, deployment, project
resourcing, and CRM work are outside this domain.

## Formats

| Format | Declared V1 set | Working now |
|---|---:|---:|
| `.md` | Yes | **Yes** |
| `.pdf` | Yes | No — later formats slice |
| `.docx` | Yes | No — later formats slice |
| `.txt` | Yes | No — later formats slice |
| `.xlsx`, `.pptx`, `.eml`, images | No | Skipped with reason |

Only `.md` should be used for the current build. `config/formats.yaml` declares
the intended set, while startup warns that the other readers do not exist yet.

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
The included demo folder is `sample-projects/intake-portal`.

The application listens on `127.0.0.1` only by default; to expose it beyond
this machine, change `APP_HOST` and the `app` service's `ports:` mapping in
`docker-compose.yml`.

## Test

```bash
docker compose run --rm app pytest
```

Last verified on the `bind-and-review-replay` branch: **55 passed**, real
PostgreSQL, no live model key. Fresh-clone and image-only verification remain
open release checks; this is a verified development-worktree command, not yet
a fresh-machine claim.

## Configuration

| File | Purpose |
|---|---|
| `config/formats.yaml` | Declared extensions and document page limit |
| `config/model.yaml` | OpenRouter model, endpoint, rates, attempts, timeout |
| `config/rules.yaml` | User-editable R1–R4 rule set for the later Examine slice |

Rules/findings are designed but not implemented. Editing `rules.yaml` therefore
does not change current Slice-1 output yet.

## Current limitations

- Only Markdown ingestion works; PDF/DOCX/TXT readers are not built.
- Document-type bucket validation is incomplete; only `unrelated` currently
  changes control flow.
- The durable per-project lock and waiting queue are built, but dedicated
  concurrency tests are pending.
- A kill after a model response but before its checkpoint can repeat that one
  paid call; earlier completed calls and register rows do not duplicate.
- A run waiting for Review holds the project lock; later files wait.
- Findings/rules, watched-folder auto-start, MCP, React, focused incremental
  updates, unchanged-row proof, and cost/timing reporting are later slices.
- The audit schema cannot yet record finding-attachment events.
- A rejected finding will not automatically return if later evidence makes it
  stronger.
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
