# config

Everything that should be changeable without touching code lives here.

| File | Holds |
|---|---|
| `rules.yaml` | The rules the register is judged against in Examine. A default set ships with the repo so a fresh clone runs; set `RULES_CONFIG_PATH` to point at your own file instead. |
| `formats.yaml` | The accepted file-format extensions (`.pdf`, `.docx`, `.md`, `.txt`) and the document page limit. Removing a format disables it; adding one only works if a reader for it exists in `app/ingest/` — a startup check says so if not. |
| `model.yaml` | The OpenRouter model name and base URL. Its `call:` block holds the model-call attempt count and per-call timeout. A working default ships with the repo; the API key is not stored here and comes from the environment. |
| `watcher.yaml` | `poll_seconds`, how often each project's source folder is looked at, and `quiet_seconds`, how long that folder must stop changing before the run reading it starts by itself. Set `WATCHER_CONFIG_PATH` to point at your own file instead. |
| `projects.yaml` | `projects_root`, the folder the Add-project box's dropdown lists the contents of. Ships as `sample-projects`, and must stay a relative path inside the repository — an absolute root is refused, because project creation refuses absolute folders and the dropdown would otherwise offer some. The system never creates a folder inside it or discovers a project by itself — a person puts a new client's folder there. |

Adding a rule, changing which formats are accepted, or changing how quickly the
watcher reacts, is an edit here, never a code change.

## Editing `watcher.yaml`

The shipped values are `poll_seconds: 10` and `quiet_seconds: 30`. Both must be
numbers above zero; anything else stops the application at startup, naming the
key and what is wrong with it.

- Whatever the watcher first sees in a project's folder is not an arrival. It
  starts nothing by itself, and `POST /runs` reads it exactly as before.
- A file that arrives afterwards starts a run once the folder has stopped
  changing for `quiet_seconds`.
- Nothing starts while that project already has a run running, at review, or
  queued. Files that arrive during a review wait for the run after it.
- The watcher forgets what it has seen when the application restarts, so files
  that arrived while it was down are read by the next run started by hand.

## Editing `rules.yaml`

Each rule needs an `id` and a `text`, and may carry `params` the text refers to,
such as `max_days`. Ids must be unique, and `D1` and `D2` are reserved for the
two deliverable checks the system runs itself.

A run parses this file when it starts and keeps that copy for its whole life,
alongside a fingerprint of the parsed rules — comments and layout do not change
the fingerprint, a value such as `max_days` does. So:

- An edit applies to the **next run**. It never changes what a run already
  under way is examining, and it never re-opens a run that already finished.
- A run resumed after a crash still uses the rules it froze, even if the file
  changed or broke in the meantime.
- A file that cannot be read as a rules list fails the run at its first stage,
  naming what is wrong and what to fix. It is never treated as "no rules".

There is no per-rule change detection: the register is small, so a rules change
means the whole register is examined again in one call by the next run.
