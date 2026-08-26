# Requirements-to-Delivery Register

A client hires a software provider to build something. Along the way, four
kinds of document get written: meeting notes, a scope document, a handover
note, and a testing report.

The problem is that no single document answers the question everyone actually
has. For each thing the client asked for: **Was it written down? Was it built?
Did testing find it working? Where does it stand today?** To answer that, you
have to open all four documents and match them up by hand.

This system does that matching for you. It reads the documents and builds one
table, called the **register**. Each row is one thing the client asked for. Each
cell says which file it came from, which section of that file, and the exact
words. Silence is recorded too: when a document was read and said nothing
about a row, the cell names that file and says so. Nothing is added to the
register until a person approves it.

The system is small on purpose. It reads two file formats, covers one kind of
work, and only adds rows — it never deletes or rewrites them. Everything it
cannot do is listed under [What it does not do](#what-it-does-not-do).

## What it produces

The four sample documents in `sample-documents/helpline-ai/` contain seven
requirements. Reading all four produces this register:

| Row | What was asked | Written down | What testing found | Status |
|---|---|---|---|---|
| 1 | BrightCart wants an AI system that answers support-line calls. | Yes | The voice agent answered questions correctly every time it was tested. | `Done` |
| 2 | BrightCart wants a chat bot on their website for customers who would rather type. | Yes | The chat widget passed testing and answered correctly every time. | `Done` |
| 3 | BrightCart wants the support bot available on WhatsApp. | Yes | The WhatsApp bot could not be found or reached during testing. | `Not delivered` |
| 4 | BrightCart wants one dashboard containing all call and chat transcripts. | Yes | Chat transcripts appeared. The call-transcripts part was unfinished. | `Partial` |
| 5 | BrightCart wants a weekly report of call and chat volumes and resolutions. | Yes | Not mentioned | `Handed over` |
| 6 | Support must work in Hindi and English. | Yes | Not mentioned | `Requested` |
| 7 | Chats the bot cannot resolve must reach a real person. | Not mentioned | Human escalation was absent from the delivered system. | `Disputed` |

The table above is the short view. Behind every row there is also its
evidence — the quotes from the documents, and where each quote came from.
On the screen, clicking a row opens a drawer with that evidence. Over MCP,
the `get_register` tool returns every row with its evidence, and it can
also return the whole register as one markdown file. Here is row 7 from
that file — the most interesting row:

```
## Row 7 — Chats the bot cannot resolve must reach a real person.

**Evidence**

- meeting-notes-02-jul.md, under "Discussion": "when a chat gets stuck and
  the bot can't help, it has to hand off to a real person." — What was asked
- client-requirements-v1.md was read, and it does not mention this ask.
  — Written down
- handover-summary.md, under "What was handed over": "We also built a 'talk
  to a human' handover: when the bot can't resolve a chat, it now hands the
  conversation across to a live agent." — Status
- testing-feedback-12-aug.md, under "What we found": "The human escalation
  is missing entirely. There is no 'talk to a human' button anywhere in the
  chat widget." — Status
```

A row can also have **Findings**. A finding is something a rule caught on
that row — for example, a requirement that was built but never written down.
The register also has a **Rules** section, listing the rules it was checked
against.

Two documents, opposite claims. The handover says it was built. Testing says it
is not there. So the status cell holds both quotes, and the row reads
`Disputed`.

The system does not pick a side. Finding the disagreement and showing the
evidence for both is the job. Settling it is not.

This row shows one more thing. The client asked for human escalation in a
meeting, but nobody wrote it into the scope document. `Written down` says that
plainly instead of leaving the cell empty.

### The statuses

A row starts at `Requested`. It moves only when a document says something
about it, and every move keeps the quote behind it.

| Status | Meaning |
|---|---|
| `Requested` | The client asked for this, in a meeting or in the written scope. The provider and testing have said nothing about it yet. |
| `Handed over` | A handover note says it is built. Nobody has tested it yet. |
| `Done` | Testing tried it and it worked. |
| `Partial` | It was delivered, but testing found it broken or unfinished. |
| `Not delivered` | Testing says it is missing, and no handover note ever claimed it was built. |
| `Disputed` | A handover note says it is built, but testing says it is missing. Both quotes stay on the row. |

`Not mentioned` is a cell value, not a status. When a document was read and
said nothing about a row, that cell is written as `Not mentioned` — and the
status stays where it was. In row 6 above, the testing report said nothing
about Hindi and English, so "What testing found" reads `Not mentioned` and
the status stays `Requested`.

Two things in a testing report never move a status:

- A **change request** — the client asks for something new during testing.
  In the sample, "the widget should also send an SMS follow-up" is a new
  ask, not a verdict, so the chat widget stays `Done`.
- A mention with **no verdict** — the report mentions the row but never
  says whether it worked or not.

Both are recorded on the run, and the register does not change.

### The rules

`config/rules.yaml` holds rules the register is checked against. Four come with
the repository:

- Anything built must have a written requirement; a verbal mention is not enough.
- Testing feedback asking for new behaviour is a change request, not a bug.
- Every written requirement must have a testing outcome.
- No register row is `Done` without a testing outcome.

When a rule is broken, the system asks a question instead of changing
anything. Approve it and the finding is attached to the row; reject it and
it stays only in the run's record.

A rule can wait for its documents: with `applies_when`, it is not checked
until the kinds of document it lists have been read. Rules are edited only
in `config/rules.yaml` — more details are in
[config/README.md](config/README.md).

## Run it

You need Docker with Docker Compose. You also need Node once, to build the
UI.

```bash
cp .env.example .env
```

Open `.env` and set `POSTGRES_PASSWORD` to anything. To do a real run, also set
`OPENROUTER_API_KEY`. Without that key the application still starts, but a run
cannot begin and it tells you why.

Now build the UI and start everything:

```bash
npm --prefix ui ci && npm --prefix ui run build
docker compose up --build
```

### What you should see

Open `http://localhost:8000/ui/` — you get a screen with three columns and an
empty project list. The application never creates a project on its own; you
create one over a folder.

To watch a full run, make an empty folder:

```bash
mkdir sample-projects/helpline-ai
```

On the screen, press **Add project +** and pick that folder. The folder has no
files in it, so there is nothing to run yet: the project is created and no run
starts. Now copy the first document in:

```bash
cp sample-documents/helpline-ai/meeting-notes-02-jul.md sample-projects/helpline-ai/
```

Nobody has to press anything. The folder is watched every 2s, and once the file
has stopped changing for 5s the first run starts by itself. You will see its
progress move through Ingest, Extract, Match and Examine, and then stop at
Review.

It stops there because it needs you. Open the **Run** tab and answer the
questions this run raised. Then press **Add this run's changes to the register**.

That is when the register is written. This meeting note names seven things the
client wants, so the register now holds seven rows. Open it and every row shows
its quote from the meeting note.

Copy the remaining documents in the same way, one at a time, in the order
the work happened:

```
1.  meeting-notes-02-jul.md        already added — created the seven rows
2.  client-requirements-v1.md      fills in Written down
3.  handover-summary.md            says what was built
4.  testing-feedback-12-aug.md     says what testing found
```

Each new document starts its own run, and each run moves the rows that
already exist. After the fourth one the register looks like the one at the
top of this file.

`sample-documents/helpline-ai/README.md` explains the sample documents and the
seven requirements inside them.

## Test it

The tests never call a real model — they use a scripted one that returns fixed
answers. So `OPENROUTER_API_KEY` is needed for a real run, and never for the
tests.

The Python tests need Docker, because they run against a real PostgreSQL
database:

```bash
docker compose run --rm app pytest
```

The front-end tests need neither Docker nor a database:

```bash
npm --prefix ui test
```

## What it accepts

### One kind of work

It reads documents from one kind of work: a client asks for software, the
provider builds and hands it over, and the client tests it and sends
feedback. That whole journey — nothing else.

It does not cover sales, pricing, contracts, invoices, deployment, staffing or
CRM work.

### Four kinds of document

| Kind | What it does to the register |
|---|---|
| Meeting notes | Creates rows |
| Client requirements document | Fills in `Written down` for existing rows; a written ask that has no row yet creates one |
| Handover summary | Moves existing rows. Creates none. |
| Testing feedback | Moves existing rows. Creates none. |

A handover note or testing report that arrives before the requirement it talks
about has no row to move. Instead of guessing, the system lists it on the
**Skipped** tab and explains why.

### Two file formats

| Format | Read | Where a quote is located |
|---|---|---|
| `.md` | Yes | Nearest heading |
| `.pdf` | Yes | Page number |
| Anything else | No, and the reason is recorded | — |

`config/formats.yaml` holds this list and the 20-page limit. A document is
skipped — with the reason shown on the run — when it is longer than that
limit, when a PDF is password-protected, or when a PDF is a scan with no
text in it. Such a document has not been read, and the system does not
remember it as read: fix the file — for example, export the PDF without its
password — and the next run reads it on its own.

## Two ways to use it

There are two ways to use the system: the UI for a person, and the MCP tools
for a machine. Both call the same code, so both get the same answer — the
same register, the same questions, and the same refusal when something is
not allowed.

### The UI

`http://localhost:8000/ui/` has three columns: projects on the left, the
chosen project's register and runs in the middle, and the open run on the
right.

A run has three tabs:

| Tab | What it shows |
|---|---|
| Run | The run's steps, its questions, what pressing Add will write, and the rules it was judged against |
| Skipped | Every file and quote this run did not use, and why |
| Reported instructions | Any line in a document that tried to give the system an instruction — shown, never followed |

The **Register** view shows the project's register as one table, with a
drawer per row holding its cells, evidence, findings and history.

### MCP tools

Eight tools, served by the running application at
`http://localhost:8000/mcp/`. Nothing connects on its own — point your MCP
client at that address. For Claude Code, that is:

```bash
claude mcp add --transport http register http://localhost:8000/mcp/
```

| Tool | Arguments |
|---|---|
| `create_project` | `source_folder_path` — creates it, or returns the existing one. The name comes from the folder. |
| `list_projects` | no arguments — returns every project and its runs |
| `start_run` | `project_id` |
| `get_run_status` | `run_id` — the run's progress, its questions, and what Add will write |
| `submit_decision` | `run_id`, `decision_id`, `outcome` (`approved` / `rejected`) |
| `finish_review` | `run_id`, `add_to_register` |
| `get_register` | `project_id`, `register_format` (`json` / `markdown`) — each row carries its `evidence` |
| `get_history` | `project_id` — what changed, when, and from which document |

A run is not a single call. `start_run` returns an id straight away, and you
poll `get_run_status` until it is done. Nothing is written to the register until
`finish_review` is called with `add_to_register` set to true. Call it with false
and the run ends as `discarded`, leaving the register untouched.

## Configuration

Rules, accepted formats, the page limit, the model, and the watcher's timing
are all edits to files under `config/` — each file is described in
[config/README.md](config/README.md). One setting lives outside it:
`ui/config/screen.json`, how often the screen refreshes.

## What it does not do

**Every document is read only once.** If a file comes back with the same
name or the same content, the system knows it has already read it, and
skips it.

This is deliberate. If a changed document were read again, the system would
quietly rewrite rows a person had already approved. So instead:

- Deleting a document changes nothing. The rows it produced stay.
- Removing a requirement from a document does not remove its row. Nothing here
  takes back a row that was approved.
- Files inside sub-folders are not read. Only files sitting directly in the
  project's folder are.

A skipped file shows on the **Skipped** tab with its reason. Two things
never show there: a deleted file and a sub-folder.

The rest of the limits:

- **Rules about time cannot be checked.** A rule like "nothing stays blocked
  more than N days" has nothing to count from, because the register stores no
  dates from the documents.
- **The register shows only the latest run's findings.** Every run that
  applies a rule re-examines the whole register, so a clean run clears an
  older finding — like a test dashboard, which shows today's result, not
  yesterday's. Earlier findings stay in the row's history, under the run that
  raised them. The cost: if the model misses a still-broken rule, its finding
  disappears until a later run raises it again.
- **A rule that keeps failing asks its question again on every run.** No row
  is ever done being checked, so the same question can come back run after
  run.
- **A finding's evidence is not double-checked.** The model writes the
  evidence line, and the system only checks that it wrote something — not
  that the words really come from the document. The person reviewing the
  question is the check.
- **A failed run does not restart itself.** Nothing it read counts as read,
  so the next run picks those documents up again.
- **A crash can repeat one paid model call.** If the application dies between
  a model's reply and saving it, the resumed run makes that call again —
  everything already saved stays saved.
- **There is no login.** Nothing checks who is calling. The MCP endpoint
  refuses any request whose `Host` is not `localhost`, so another machine
  cannot call the tools as it stands.
- **A project's folder must sit directly inside `sample-projects/`** (the
  folder named in `config/projects.yaml`). Anywhere else is refused, with the
  reason and the fix.
