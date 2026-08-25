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
words — or, when a document was read and said nothing about the row, which
file that was. Nothing is added to the register until a person approves it.

The system is small on purpose. It reads two file formats, covers one kind of
work, and only adds rows — it never deletes or rewrites them. Everything it
cannot do is listed under [What it does not do](#what-it-does-not-do).

## What it produces

The four sample documents in `sample-documents/helpline-ai/` contain seven
requirements. Reading all four produces this register:

| Row | What was asked | Written down | What testing found | Status |
|---|---|---|---|---|
| 1 | BrightCart wants an AI system that answers support-line calls. | Yes | The voice agent answered questions correctly every time it was tested. | `Done` |
| 3 | BrightCart wants the support bot available on WhatsApp. | Yes | The WhatsApp bot could not be found or reached during testing. | `Not delivered` |
| 4 | BrightCart wants one dashboard containing all call and chat transcripts. | Yes | Chat transcripts appeared. The call-transcripts part was unfinished. | `Partial` |
| 6 | Support must work in Hindi and English. | Yes | Not mentioned | `Requested` |
| 7 | Chats the bot cannot resolve must reach a real person. | Not mentioned | Human escalation was absent from the delivered system. | `Disputed` |

The table above is the short view. Below it the file writes out every row's
evidence: one line per thing a document said, naming where it was said, the
words themselves, and the cells they support. Where a document was read and
said nothing about the row, the line says that instead. Row 7 is the one
worth opening, so here it is as the file writes it:

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

A row a rule found something on also gets a **Findings** list — the rule in
its own words, the run that raised it, and what that run found. A row nothing
was found on gets no such list at all. The file closes with a **Rules**
section naming the rules the newest run actually applied, so an empty
findings list is read beside what produced it.

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

| Status | What it means | What puts a row here |
|---|---|---|
| `Requested` | The client asked for this. No document read so far says whether it was built or tested. | No handover note and no testing report has said anything about it — a document that was read and silent about the row leaves it here |
| `Handed over` | The provider says it is built. Nobody has tested it yet. | A handover note, with no testing report about it |
| `Done` | Testing tried it and it worked. | A testing report that passed it |
| `Partial` | It exists, but testing found it broken or unfinished. | A testing report that found a defect |
| `Not delivered` | Testing looked for it and it was not there, and no handover note ever claimed it was built. | A testing report that found it missing |
| `Disputed` | A handover note says it is built. Testing says it is missing. Both quotes stay on the row. | A handover note and a testing report that contradict each other |

Two things testing can say move nothing. A **change request** — a new ask that
turns up during testing — is not a verdict on the work already done. And a note
with **no verdict in it** is not a verdict either. Both are recorded on the run
and left off the status.

### The rules

`config/rules.yaml` holds rules the register is checked against. Four come with
the repository:

- Anything built must have a written requirement; a verbal mention is not enough.
- Testing feedback asking for new behaviour is a change request, not a bug.
- Every written requirement must have a testing outcome.
- No register row is `Done` without a testing outcome.

When a rule is broken, the system asks a question instead of changing anything.
The question names the rule, the row, what went wrong, and the evidence. Approve
it and the finding is attached to the row. Reject it and the finding stays in
the run's record, off the register.

A rule waits for the documents it is about. Each rule may list them under
`applies_when`, and the rule is checked only once every kind it lists has been
read for the project:

```yaml
  - id: R4
    text: "Every written requirement must have a testing outcome."
    applies_when:
      - testing feedback
```

The four values allowed there are the four kinds of document this system reads:
`meeting notes`, `client requirements document`, `handover summary`, `testing
feedback`. Anything else stops the application at startup and says which rule
named it. A rule with no `applies_when` is checked whenever the register is
examined.

Without this, a rule about testing outcomes is checked before any testing
report has been read, and it reports the silence as a fault on every row.

Each run reports which rules actually ran, so a rule still waiting is not
counted as one that found nothing.

Editing `config/rules.yaml` is the only way to add or change a rule. The screen,
the API and the tools can all show which rules ran, but none of them can change
one.

## Run it

You need Docker with Docker Compose. You also need Node once, to build the
review screen.

```bash
cp .env.example .env
```

Open `.env` and set `POSTGRES_PASSWORD` to anything. To do a real run, also set
`OPENROUTER_API_KEY`. Without that key the application still starts, but a run
cannot begin and it tells you why.

Now build the screen and start everything:

```bash
npm --prefix ui ci && npm --prefix ui run build
docker compose up --build
```

### What you should see

Open `http://localhost:8000/health` — it answers `{"status":"healthy"}`.

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

Now copy the next document in. Another run starts on its own, and this one moves
the rows that already exist. Add the four documents in the order the work
happened:

```
1.  meeting-notes-02-jul.md        creates the seven rows
2.  client-requirements-v1.md      fills in Written down
3.  handover-summary.md            says what was built
4.  testing-feedback-12-aug.md     says what testing found
```

After the fourth one the register looks like the one at the top of this file.

You can also add them two at a time — `meeting-notes` with
`client-requirements`, then `handover-summary` with `testing-feedback`. The
result is the same seven rows.

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

Documents written after a client starts describing what they want software to
do: while the provider asks questions, builds it, and hands it over, and while
the client tests it and sends feedback back.

It does not cover sales, pricing, contracts, invoices, deployment, staffing or
CRM work.

### Four kinds of document

| Kind | What it does to the register |
|---|---|
| Meeting notes | Creates rows |
| Client requirements document | Creates rows, and fills in `Written down` |
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
skipped, with the reason shown on the run, when it is longer than that limit,
when a PDF is password-protected, or when a PDF is a scan with no text in it. A
skipped document is not marked as read, so the next run tries it again.

## Two ways to use it

Every operation exists twice — once as a screen for a person, once as a tool for
a machine. Both run the same code, so both give the same answer — including
the same refusal when something is not allowed.

### The review screen

`http://localhost:8000/ui/` has three columns. On the left, every project and
what it is doing. In the middle, that project's register and its runs, newest
first. Either side column collapses to a narrow rail that still opens
everything it held. Choosing a project opens its newest run at once, and the
address carries what is on screen — `/ui/?project=<id>&run=<id>` — so a link to
one run is a link you can keep.

On the right, one run, across three tabs:

| Tab | What it shows |
|---|---|
| Run | Each step of the run, why it stopped early or failed, what it is waiting for, every question it raised, and the rules it judged against |
| Skipped | Every file and quote this run did not use, and the reason: read before, not read, or not attached to any row |
| Reported instructions | Any line in a document that tried to give the system an instruction. It is shown to you and never followed. |

The Register entry above the runs opens the project's own register instead, in
the same panel, across two tabs: **Register**, the table of rows with a mark
beside any row a rule found something on, and **History**, what changed in the
register, grouped under the run that changed it. Clicking a row opens a panel
beside the table with that row's four cells in full, the evidence each rests on,
its findings, and its own history. Close it with ×, Escape, or a click outside.

The screen refreshes every three seconds and only shows what the server has
confirmed. When you answer a question, the answer is sent and then the run is
read back — so if the server refuses your answer, the question stays unanswered
on screen with the server's reason next to it. If the application cannot be
reached at all, a strip says so and the last known state stays on screen,
unchanged.

If `ui/dist` has not been built, `/ui` answers `503` and tells you the build
command, instead of a plain `404`.

### MCP tools

Eight tools, served by the running application at `http://localhost:8000/mcp/`
over streamable HTTP.

| Tool | Arguments |
|---|---|
| `create_project` | `source_folder_path` — creates it, or returns the existing one. The name comes from the folder. |
| `list_projects` | *(none)* — every project, with its runs |
| `start_run` | `project_id` |
| `get_run_status` | `run_id` — each decision as one whole text and as the parts it was built from |
| `submit_decision` | `run_id`, `decision_id`, `outcome` (`approved` / `rejected`) |
| `finish_review` | `run_id`, `add_to_register` |
| `get_register` | `project_id`, `register_format` (`json` / `markdown`) — each row carries its `evidence` |
| `get_history` | `project_id` — what changed, when, and from which document |

A run is not a single call. `start_run` returns an id straight away, and you
poll `get_run_status` until it is done. Nothing is written to the register until
`finish_review` is called with `add_to_register` set to true. Call it with false
and the run ends as `discarded`, leaving the register untouched.

Any MCP client that speaks streamable HTTP can connect to that address.

The same eight operations are also HTTP endpoints. `/docs` lists them.

## Configuration

Adding a rule, a format, a limit or an interval is an edit to one of these
files. None of it requires changing code.

| File | Holds |
|---|---|
| `config/rules.yaml` | The rules the register is checked against, and the document kinds each one waits for (`applies_when`) — the only place a rule can be added |
| `config/formats.yaml` | Which file extensions are read, and the page limit |
| `config/model.yaml` | Which model to call, and its endpoint, retries, timeout and reasoning effort |
| `config/projects.yaml` | The folder that the Add-project dropdown lists |
| `config/watcher.yaml` | How often a folder is checked (2s) and how long it must be quiet before a run starts (5s) |
| `ui/config/screen.json` | How often the screen refreshes |

A run takes a copy of the rules when it starts. Editing the file affects the
next run, never one already going.

## What it does not do

**A document is read once, and only once.** The system recognises it by its
name or by its contents — either one is enough.

This is a choice, not an oversight. Reading a changed document again would mean
rewriting a row a person had already approved, based on evidence that person
never saw. So instead:

- Deleting a document changes nothing. The rows it produced stay.
- Removing a requirement from a document does not remove its row. Nothing here
  takes back a row that was approved.
- Files inside sub-folders are not read. Only files sitting directly in the
  project's folder are.

Any file that gets skipped is listed on the **Skipped** tab with the reason.
Two cases cannot be listed: a deleted file is no longer there to find, and a
sub-folder is not a file.

The rest of the limits:

- **Rules about time cannot be checked.** A rule like "nothing stays blocked
  more than N days" has nothing to count from, because the register stores no
  dates from the documents.
- **An unanswered possible match is checked as the match it asks about.** While
  the question is open, the rules are checked against the existing row rather
  than against the new one. If you then reject the match, the new row gets no
  finding in that run. The next run checks it like any other row.
- **A rule that ran before may not raise the same finding again.** A rule is
  judged by a model, so a later run that checks the same row may or may not
  repeat what an earlier run found. The register shows the newer answer, and
  the History tab keeps the older one.
- **A rule that keeps failing asks its question again on every run.** A rule is
  checked against the row as it stands right now, so no row is ever done being
  checked. The cost is the same question coming back run after run.
- **The evidence in a finding is not checked against the row.** It is only
  checked for not being empty. If the model paraphrases instead of quoting,
  nothing catches it.
- **A rejected finding does not come back** if later evidence would make it
  stronger. An approved one is not looked at again.
- **A handover only ever moves a row to `Handed over`.** A handover that says
  the work is partly there still reads `Handed over`, because `Partial` is
  testing's word for what testing found. Testing moves the row when it runs.
- **A rule never runs against something that reached no row.** A testing note
  asking for new behaviour that matched no requirement is shown on the
  **Skipped tab** and no rule is applied to it. A rule sees register rows
  only.
- **A failed run does not restart itself**, and nothing it read counts as read.
  The next run reads those documents again from the start.
- **A run waiting at Review blocks its project.** Files that arrive meanwhile
  wait for the next run.
- **The watcher forgets what it has seen when the application restarts.** A file
  that arrived while it was down will not start a run by itself. The next run
  you start by hand picks it up.
- **Two documents of the same kind in one batch** are read in file-name order.
  That is fine while they say different things, and undecided if they ever say
  the same thing.
- **A crash between a model reply and saving it can repeat that one paid call.**
  Earlier calls and register rows are not duplicated.
- **Nothing checks who is calling** — not the screen, not the API, not the
  tools. The MCP endpoint refuses any request whose `Host` is not `localhost`
  or `127.0.0.1`, so another machine cannot reach it as it stands.
- **The production image builds the screen in a pinned Node stage.** The final
  Python image contains `ui/dist` but no Node runtime. The broad Compose source
  bind remains a development convenience, not proof of packaged contents.
- **A project's folder must sit directly inside** the folder named in
  `config/projects.yaml` (`sample-projects/` by default). Not the root itself,
  not nested deeper, never an absolute path. Anything else is refused, with the
  reason and the fix.
