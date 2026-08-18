# doctask-aditya-lingwal

An agentic system that reads software requirements-to-delivery documents and
builds a grounded **Requirements-to-Delivery Register**. Each row traces one
client requirement through written scope and testing. Exact source evidence and
a human approval gate prevent unsupported rows from reaching the register.

## Current working scope

Slice 1, the formats and types slice, the rules and findings slice, the MCP
slice, the incremental update slice, and the review screen are implemented:

`Document folder → Ingest → Extract → Match → Examine → Review → Commit → the register, read live as JSON or Markdown`

- PostgreSQL stores projects, runs, documents, register rows, citations,
  review decisions, findings, audit entries, and LangGraph checkpoints.
- FastAPI exposes eight endpoints, and the same eight operations are MCP tools
  served by the same process over the same core functions.
- A run returns immediately, continues in the app process, and is polled.
- A run reads only files it has never read before — new by name and by
  content — and leaves every row an unaffected file supplied byte-identical,
  fingerprint included.
- Each project's folder is watched, and a file that arrives there starts a run
  by itself once the folder has settled.
- Review decisions are one proposal at a time; nothing reaches the register
  until approved.
- One browser page at `/ui` shows a run and answers its gates.
- Four kinds of document are read, in the order the work happens: **meeting
  notes → client requirements document → handover summary → testing feedback**.
  The first two create rows; the last two move rows that already exist and
  create none. They may arrive one per run or several together in one run, and
  a batch is read in that order whatever the files are named. A document that
  arrives before the requirement it talks about is reported on the Not used tab
  rather than acted on.
- One ask stated in two documents of one batch becomes **one** row citing both
  — the meeting note that raised it and the requirements document that wrote it
  down — and that row says the ask is in writing. Where the match is uncertain,
  two rows are proposed and the reviewer is asked which is right.
- A line inside a document addressed to the system is reported on the run and
  on the screen, and never followed — and that document is still read. It is
  deliberately not part of the register, which is what the client is sent.
- Examine judges the whole register against the rules the run froze and raises
  a finding as a question, never as an edit.
- Startup resumes a run killed mid-flight from its durable checkpoint.
- Automated tests use a scripted model and no live API key.

No live hosted-model run has been completed yet. Current proof is for the
orchestration, persistence, validation, review, and register-read paths using
the scripted client.

## The register's cells, its statuses, and what moves them

A row has four cells, each carrying its own citations:

`What was asked` · `Written down?` · `What testing found` · `Status`

Every row starts at `Nothing said yet` and moves only on what a document says.

| Status | What it means |
|---|---|
| `Nothing said yet` | Nothing read so far says whether this was delivered or tested. It makes no claim. |
| `Done` | A document reports the work exists and behaves as asked. |
| `Partial` | A document reports the work exists but is wrong or incomplete. |
| `Not delivered` | A document states the work is not there. A positive claim, and it needs a citation. |
| `Handed over` | A handover summary reports the work exists; testing has not spoken yet. |
| `Disputed` | Two documents make opposing claims. The system never resolves it; it goes to a person. |

Testing feedback moves a row by its label: `Passed` makes it `Done`, `Defect`
makes it `Partial`, and `Change request` and `Unclear` move no status — a new
ask arriving during testing is not a verdict on the work. A handover summary
with no testing behind it makes the row `Handed over`: it says the work exists,
never that it behaves as asked.

`Status` keeps the citation of every document that still supports what it says,
so a row that reads `Done` names both the handover that said the work exists
and the testing document that said it behaves as asked. A superseded testing
verdict is dropped, because it proves something the cell now denies.

Attaching a document's evidence to a row that is already committed is asked
about before it happens, and so is any link the system is unsure of. An
observation about no requirement the register traces is reported on the
Not used tab rather than forced onto the nearest row.

Testing feedback carries one of five labels — `Passed`, `Defect`, `Not found`,
`Change request`, `Unclear`. `Not found` is what reaches the last two statuses:
with a handover claiming delivery it is `Disputed`, and without one it is `Not
delivered`. Neither synthetic corpus contains a handover contradicted by
testing, so `Disputed` is proven by test rather than by a corpus run.

## Rules and findings

`config/rules.yaml` holds the rules the register is judged against; R1, R2, R4
and R5 ship with the repository. Editing that file is the only way a rule
enters the system — no screen, endpoint or MCP tool can add or change one, and
none of them is judged anywhere but in that file.

Examine runs once per run, between Match and Review, in a single model call for
the whole register. Each finding names its rule, the row it is about, what it
found, and the evidence — and becomes a question the Delivery Owner answers.
Approving one attaches it to the row; rejecting one keeps it in the run record
and off the register. A finding never edits a cell, and attaching one does not
change the row's fingerprint, which covers the four cells only.

A run with nothing wrong says so: `GET /runs/{id}` and the register, in both
its formats, name the rules that ran and how many rows they ran against,
alongside an empty findings list.

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

## What this does not do, and why

A run reads a document exactly once in a project's lifetime, keyed by its name
or its content — either alone is enough to count it as already read. This is a
deliberate boundary, not an oversight: re-reading a changed document to notice
it stopped asking for something would mean changing an already-committed row
on evidence no person had seen, and that path has never run against a live
model. A smaller system that only ever adds to the register, with its
boundary written down here, is worth more than a larger one whose edges were
never exercised.

- **Deleting a document does nothing.** The rows it supplied stay in the
  register exactly as they were.
- **Renaming a document does nothing.** Its content has already been read,
  under the old name.
- **Editing a document does not cause it to be read again.** To have a
  revision read, save it under a new name.
- **A requirement removed from a document does not remove its row.** Nothing
  in this system takes a committed row back.
- **Replacing a document with an entirely different one under the same name
  is not used**, because that name has already been read. Give a new document
  a new name.
- **Sub-folders are not read.** Only files directly in the project's folder
  are.

A file that is still in the folder and gets passed over says so: the run's
`Not used` section names it and gives the reason, so an edited, renamed or
replaced document is never quietly ignored.

Two of these are silent, and cannot be otherwise. A deleted document is no
longer a path for Ingest to enumerate, and a sub-folder is not a file, so
neither reaches the point where a skip is recorded. Nothing names them; a run
that finds no new document says only that.

## Rules that changed and documents that did not

When no document has changed but the rules in `config/rules.yaml` have, the run
skips Extract and Match and examines the existing register against the new
rules. It is the same run, routed differently, and it ends at the same
review-ending gate.

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
| `.docx`, `.txt`, `.xlsx`, `.pptx`, `.eml`, images | No | Not read, with reason | — |

`config/formats.yaml` declares which extensions are accepted and the document
page limit, currently 20 pages. A file whose extension is not listed there
never reaches a reader, and startup warns if the file names a format no reader
exists for.

A document is not read, with its reason recorded on the run, when it is longer
than the page limit, when a PDF is encrypted, and when a PDF has no text layer
because it was scanned. The page limit applies to PDFs, the only declared
format that reports a page count. None of these is written to the `documents`
table, so unlike a document that was read and finished with, one that was not
read is not "already read" — the next run reads it again, and pays for it again if a
model call was what failed.

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
`{"status":"healthy"}`. Startup creates no project of its own — `GET
/projects` lists nothing until an operator creates one, over a folder that
already sits directly inside `sample-projects/`, with `POST /projects` or the
screen's Add-project box. The generated API schema at `/docs` shows the eight
operations:

- `POST /projects`
- `GET /projects`
- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/decisions`
- `POST /runs/{id}/finish-review`
- `GET /projects/{id}/register?format=json|markdown`
- `GET /projects/{id}/history`

## The review screen

One screen shows the runs the application knows about and answers one run's
gates. Build it once, then start the application:

```bash
npm --prefix ui ci && npm --prefix ui run build
docker compose up --build
```

Open `http://localhost:8000/ui/`. Until `ui/dist` exists, `/ui` answers `503`
with the build command above rather than a bare `404`.

The viewport is three columns. On the left, every project: a status mark
(a lime dot pulsing while a run works, a lime ring while one waits at review,
a grey ring when nothing on it is live), its run count, the date of its most
recent run, and — only while something is live — the active run's stage strip
or how many decisions it is waiting on. No folder path appears on a card.
A full-width **Add project +** button sits at the bottom of this column in
every state, empty or not; it opens a box with a dropdown of the folders
inside the configured projects root that do not already carry a project
(never invented, never created by the screen; when none are left the
dropdown stays where it is, disabled, reading "No folder left to add.") and a
**Create and start run** button. There is no name field — a project's name is
derived from its folder, on the server, and cannot be typed. The box refuses
to send an unchosen folder in its own words; every other rule, including
whether the folder actually exists or sits inside the configured projects
root, is the server's, shown under "Could not create this project" exactly
as it answered.

The middle column lists the selected project's own **Register** — its live
committed row count, once any run has committed — above that project's
runs, newest first: run number, when it started, and either its live stage
strip, its status, or — on a run that ended `done` — the register's current
committed row count. The column
collapses to a narrow strip (keeping the open run's number, or "Register",
visible) so the reading pane can take the full width while it is being read.
Opening a run writes it into the address as `/ui/?run=<run id>`, so a link to
one run is a link that can be kept; no run id is ever typed. Opening the
register clears whatever run was open, and both refusals, so a previous
run's decisions never sit beside it.

To the right, one run's sections are read one at a time behind tabs:

| Section | What it shows |
|---|---|
| Stages | Every stage of the run — done, working, not needed, or pending — and the reason it ended early or failed, against the stage it failed at |
| Not used | Each file or quote this run did not use, with the reason recorded on the run and a label saying which of the three it is — already read, not read, or dropped |
| Needs your decision | Every question the run put to a person, its frozen wording and its answer, what Approve and Reject will each do, plus the rules the run was judged against, and the two buttons that end the review |
| Reported, not followed | Every line in this run's documents that tried to give the system an instruction, with the file, the place and the document's own words |

Opening the project's own **Register** entry (middle column) shows the same
right-hand panel, with the project's whole committed register — its cells,
its citations and its approved findings, read live from `register_rows`
through `GET /projects/{id}/register` — or, while the project holds no
committed row, the line "Nothing has been added to this register yet."

Under it, a **HISTORY** section reads the audit trail through
`GET /projects/{id}/history`: what changed, when, and because of which
document, newest first. A row's arrival is one line — `Row 1 · Row created`
— rather than one line per cell, an approved finding is its own line, and a
cell change reads `Row 1 · Status: Nothing said yet → Done` with the run
number and the source file under it. A project whose trail is empty reads
"No history yet." The section carries a **NOTE** chip reading "Not part of
the exported register.", because it is not: the register export is the
cells, their evidence and the findings, and this is the record of how they
got there.

The page polls `GET /projects` and `GET /runs/{id}` every **3 seconds**
unconditionally — whatever is on screen, whatever a run's status is — and
`GET /projects/{id}/register` and `GET /projects/{id}/history` on the same
interval while the register panel is open; that interval lives in
[`ui/config/screen.json`](ui/config/screen.json). This is
deliberate: at this size the payload is a few kilobytes, and one
unconditional read is easier to reason about than conditional refresh rules.
If a poll cannot reach the application at all, a strip under the header says
so and whatever was last read stays on screen underneath, unchanged; a
refusal the application did answer (a run that does not exist, say) is shown
beside the data it refused, not as that strip. Nothing shown comes from what
was clicked: an answer is posted to `POST /runs/{id}/decisions` and the run is
then read back, so a refused answer leaves the decision unanswered on screen
with the server's own reason beside it. Approve and Reject appear only while
the server reports the run at review, and the two buttons that end it —
**Add this run's changes to the register** and **Discard this run's changes**
— only once no decision is unanswered; the server refuses both otherwise. One
press ends the review: it records the answer it carried and runs Commit, or
ends the run `discarded` with the register untouched.

The dev-only middleware under `ui/demo/`, served by `npm --prefix ui run dev`,
**no longer works with this screen**: it answers the removed `GET /runs` and
has no `GET /projects`, which the screen now reads before it renders anything,
so those pages stay on `Loading…`. Use the application itself. None of that
folder reaches a build.

Its own tests run without Docker and without a key:

```bash
npm --prefix ui test
```

Last verified on the `helpline-ai-corpus` branch: **63 passed across 36 files**.

## Drive it from a machine

The same eight operations are MCP tools, mounted in the running application at
`http://localhost:8000/mcp/` over the streamable-HTTP transport. Each tool
calls the core function its endpoint calls, so one operation answers the same
through either door — including its refusal, which arrives with the cause and
the practical fix the endpoint would have given.

| Tool | Arguments |
|---|---|
| `create_project` | `source_folder_path` — get-or-create; no name (derived from the folder) |
| `list_projects` | *(none)* — every project, each with its runs nested |
| `start_run` | `project_id` |
| `get_run_status` | `run_id` |
| `submit_decision` | `run_id`, `decision_id`, `outcome` (`approved` or `rejected`) |
| `finish_review` | `run_id`, `add_to_register` — yes adds this run's changes to the register, no discards them |
| `get_register` | `project_id`, `register_format` (`json` or `markdown`) |
| `get_history` | `project_id` — what changed in the register, when, and from which document |

A run is not one call here either: `start_run` returns a run id at once and
`get_run_status` is polled until the run says it is done. Nothing commits
until `finish_review` is called with `add_to_register` true; called with
false, the run ends `discarded` and the register is unchanged.

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

The test suite drives the tools exactly this way; see
`tests/interfaces/mcp_client.py`.

The application currently reads project folders from inside the repository.
`sample-projects/` starts empty; a corpus for the first live-model run is
staged in by hand from `sample-documents/helpline-ai/` — see that folder's
README for what it is and the staged-copy procedure.

The application listens on `127.0.0.1` only by default; to expose it beyond
this machine, change `APP_HOST` and the `app` service's `ports:` mapping in
`docker-compose.yml`.

## Test

```bash
docker compose run --rm app pytest
```

Last verified on the `helpline-ai-corpus` branch: **246 passed**, real
PostgreSQL, no live model key. Fresh-clone and image-only verification
remain open release checks; this is a verified development-worktree command,
not yet a fresh-machine claim.

## Configuration

| File | Purpose |
|---|---|
| `config/formats.yaml` | Declared extensions and document page limit |
| `config/model.yaml` | OpenRouter model, endpoint, call attempts, timeout |
| `config/projects.yaml` | The projects root the Add-project box's folder dropdown lists |
| `config/rules.yaml` | The user-editable rule set Examine judges against, and the only way a rule enters the system |
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
- Scanned PDFs are recorded as not read rather than read; there is no OCR.
- Rules about elapsed time — "nothing stays blocked more than N days" — cannot
  be judged, because the register keeps no document dates.
- Work stopped by something outside the provider's control is reported through
  the source document, not through a cell of its own.
- A batch holding two documents of one type is read in file-name order between
  them. That is harmless while the two state different asks, and undecided if
  they ever state the same one.
- Rules are supplied by editing `config/rules.yaml`; the screen, the API and
  the MCP tools can read which rules ran but cannot add or change one.
- A handover summary that lists requirements, in a run that never ends
  `done`, is read again by the next run.
- Run events below `WARNING` are dropped as the application is shipped, because
  uvicorn's logging configuration gives the run logger no handler; warnings and
  errors still reach the container's output.
- A kill after a model response but before its checkpoint can repeat that one
  paid call; earlier completed calls and register rows do not duplicate.
- A run that fails is not restarted by itself, and nothing it read counts as
  read: because none of that run's documents finished (no extraction was
  ever written for them), the next run started on that project reads them
  again from the start.
- A run waiting for Review holds the project lock; later files wait.
- The watcher forgets what it has seen when the application restarts, so a file
  that arrived while it was down starts no run of its own; the next run started
  by hand reads it.
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
- A project's folder must sit directly inside `config/projects.yaml`'s
  configured root (`sample-projects/` by default) — not the root itself, not
  nested inside a sub-folder, and never given as an absolute path or with
  `..`; `POST /projects` refuses anything else, naming the cause and the
  fix. The Add-project box's dropdown only ever lists what that root
  actually holds on disk. Two spellings of one folder — `sample-projects/x`,
  `sample-projects/./x`, `sample-projects/x/` — reach the same project, because
  the folder is stored as the one path it resolves to rather than as the
  string a caller typed.
- `config/projects.yaml`'s `projects_root` must itself be a folder inside the
  repository, given as a relative path such as `sample-projects`. An absolute
  root is refused where the file is read: the dropdown would then offer
  absolute folders that project creation always rejects, so the two sides
  cannot be configured into disagreeing.
- The screen polls `GET /projects` and `GET /runs/{id}` unconditionally, on a
  fixed interval, whatever is on screen and whatever a run's status is —
  there is no per-project runs endpoint and no conditional refresh. At this
  size the payload is a few kilobytes, and one unconditional read is easier
  to reason about than conditional refresh rules.

## Project truth

- [`DECISIONS.md`](DECISIONS.md) — compact current decisions and limitations.
- [`PROGRESS.md`](PROGRESS.md) — current status, blockers, and next actions.
- [`documentation/decision-history.md`](documentation/decision-history.md) —
  detailed append-only decision history.
- [`documentation/progress-history.md`](documentation/progress-history.md) —
  completed progress narrative.
- `documentation/superdocs-engineering-task/superdocs-round2-working-notes.md`
  — interpreted brief requirements, separate from our decisions.
