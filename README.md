# doctask-aditya-lingwal

An agentic system that reads software requirements-to-delivery documents and
builds a grounded **Requirements-to-Delivery Register**. Each row traces one
client requirement through written scope and testing. Exact source evidence and
a human approval gate prevent unsupported rows from being exported.

## Current working scope

Slice 1, the formats and types slice, the rules and findings slice, the MCP
slice, the incremental update slice, and the review screen are implemented:

`Document folder → Ingest → Extract → Match → Examine → Review → Commit → JSON/Markdown export`

- PostgreSQL stores projects, runs, documents, register rows, citations,
  review decisions, findings, audit entries, and LangGraph checkpoints.
- FastAPI exposes six endpoints, and the same six operations are MCP tools
  served by the same process over the same core functions.
- A run returns immediately, continues in the app process, and is polled.
- A run reads only the new and changed files in the folder, and leaves every
  row they do not affect byte-identical, fingerprint included.
- Each project's folder is watched, and a file that arrives there starts a run
  by itself once the folder has settled.
- Review decisions are one proposal at a time; export is unavailable until
  approved.
- One browser page at `/ui` shows a run and answers its gates.
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

## The watched folder

Each project's source folder is looked at every **10 seconds**, and a run
starts by itself once that folder has stopped changing for **30 seconds** —
provided the project has no run already running, at review, or queued. Both
numbers live in [`config/watcher.yaml`](config/watcher.yaml), and changing
either is an edit there, never a code change.

Whatever the watcher first sees in a folder is not an arrival, so a project
created over a folder of documents starts nothing by itself. `POST /runs`
reads it exactly as before, and starting a run by hand is unchanged.

A file that arrives while a run is at review waits for the run after it.

## Withdrawal — when a document stops asking for something

When a document is read again and its new content no longer contains a
requirement **it itself supplied**, the run raises one withdrawal proposal for
that row, through the same review queue as every other decision.

- **Approve** moves that row's `Status` cell to `Withdrawn`, writes the cell
  audit, updates `Last moved`, and cites the absence: the file that was read
  again and what is no longer in it. The row's other cells, its existing
  citations and its `First seen` do not move.
- **Reject** leaves the row byte-identical, fingerprint included, and the
  rejected proposal stays in the run record.
- The row is never deleted, and neither is its history. A withdrawn row still
  appears in both exports, with its `Withdrawn` status.

Only the document a row's `What was asked` citation quotes can withdraw that
row. Another document's silence proposes nothing, because a document that never
asked for something cannot stop asking for it. Deleting a file from the folder
deletes nothing either — the rows its earlier content produced stay.

A withdrawal does not come back. If a later document asks for the requirement
again, its evidence merges onto the row the way any evidence does, and the row
still reads `Withdrawn`.

## Rules that changed and documents that did not

When no document has changed but the rules in `config/rules.yaml` have, the run
skips Extract and Match and examines the existing register against the new
rules. It is the same run, routed differently, and it ends at the same export
gate.

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

## The review screen

One page shows one run and answers its gates. Build it once, then start the
application:

```bash
npm --prefix ui ci && npm --prefix ui run build
docker compose up --build
```

Open `http://localhost:8000/ui/?run=<run id>`, or open
`http://localhost:8000/ui/` and paste a run id into the box. Until `ui/dist`
exists, `/ui` answers `503` with the build command above rather than a bare
`404`.

The page has five sections, in this order:

| Section | What it shows |
|---|---|
| Stages | The run's status and current stage, and the reason it ended early or failed |
| Skipped | Each file or quote this run skipped, with the reason recorded on the run |
| Needs your decision | Every gate the run raised, its frozen question and its answer, plus the rules the run was judged against |
| Register | The exported register, its cells, its citations and its approved findings — once the run has exported one |
| Cost and timing | That the API reports neither yet; the operations slice adds them |

The page polls `GET /runs/{id}` every **3 seconds**; that interval lives in
[`ui/config/screen.json`](ui/config/screen.json). Nothing shown comes from what
was clicked: an answer is posted to `POST /runs/{id}/decisions` and the run is
then read back, so a refused answer leaves the decision unanswered on screen
with the server's own reason beside it. Approve and Reject appear only while
the server reports the run at review, and **Finish review** only once no
decision is unanswered — the server refuses both otherwise.

Its own tests run without Docker and without a key:

```bash
npm --prefix ui test
```

Last verified on the `react-review-screen` branch: **10 passed**.

## Drive it from a machine

The same six operations are MCP tools, mounted in the running application at
`http://localhost:8000/mcp/` over the streamable-HTTP transport. Each tool
calls the core function its endpoint calls, so one operation answers the same
through either door — including its refusal, which arrives with the cause and
the practical fix the endpoint would have given.

| Tool | Arguments |
|---|---|
| `create_project` | `name`, `source_folder_path` |
| `start_run` | `project_id` |
| `get_run_status` | `run_id` |
| `submit_decision` | `run_id`, `decision_id`, `outcome` (`approved` or `rejected`) |
| `finish_review` | `run_id` |
| `get_export` | `run_id`, `export_format` (`json` or `markdown`) |

A run is not one call here either: `start_run` returns a run id at once and
`get_run_status` is polled until the run says it is done. Nothing commits or
exports without the export decision being approved first.

Any MCP client that speaks streamable HTTP can point at that URL. With the
official Python SDK:

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async with streamable_http_client("http://localhost:8000/mcp/") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        await session.call_tool("get_run_status", {"run_id": run_id})
```

The test suite drives the tools exactly this way; see `tests/mcp_client.py`.

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

Last verified on the `react-review-screen` branch: **124 passed**, real
PostgreSQL, no live model key. Fresh-clone and image-only verification remain
open release checks; this is a verified development-worktree command, not yet
a fresh-machine claim.

## Configuration

| File | Purpose |
|---|---|
| `config/formats.yaml` | Declared extensions and document page limit |
| `config/model.yaml` | OpenRouter model, endpoint, rates, attempts, timeout |
| `config/rules.yaml` | User-editable R1–R4 rule set Examine judges against |
| `config/watcher.yaml` | Folder poll interval and the quiet period before a run auto-starts |
| `ui/config/screen.json` | How often the review screen polls the run it is showing |

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
- Text in a document that addresses the system is reported and never acted on,
  but the only place that report reaches a person is the run's log line: it is
  in neither the run status nor the export.
- Run events below `WARNING` are dropped as the application is shipped, because
  uvicorn's logging configuration gives the run logger no handler; warnings and
  errors still reach the container's output.
- A kill after a model response but before its checkpoint can repeat that one
  paid call; earlier completed calls and register rows do not duplicate.
- A run waiting for Review holds the project lock; later files wait.
- The watcher forgets what it has seen when the application restarts, so a file
  that arrived while it was down starts no run of its own; the next run started
  by hand reads it.
- A row two documents both asked for raises a withdrawal proposal when either
  of them drops it. The proposal is a question, never a change, and the
  Delivery Owner answers it.
- A withdrawn row stays `Withdrawn` even if a later document asks for the
  requirement again.
- Cost and timing reporting is a later slice, so the review screen's last
  section says the API reports neither rather than showing a zero.
- `GET /runs/{id}` carries no register rows, so the review screen's register
  section stays empty until that run has exported one.
- The review screen is built by Node, which the application image does not
  carry; `ui/dist` must be built on the host before `docker compose up`, and
  the development bind mount is what carries it into the container.
- Neither the endpoints nor the MCP tools authenticate a caller, and the MCP
  endpoint answers `421 Misdirected Request` to a request whose `Host` is
  neither `localhost` nor `127.0.0.1`, so a client on another machine cannot
  reach it as it stands.
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
