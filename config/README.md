# config

Everything that should be changeable without touching code lives here.

| File | Holds |
|---|---|
| `rules.yaml` | The rules the register is judged against in Examine. A default set ships with the repo so a fresh clone runs; set `RULES_CONFIG_PATH` to point at your own file instead. |
| `formats.yaml` | The accepted file-format extensions (`.pdf`, `.md`) and the document page limit. Removing a format disables it; adding one only works if a reader for it exists in `app/ingest/` — a startup check says so if not. |
| `model.yaml` | The OpenRouter model name and base URL. Its `call:` block holds the model-call attempt count, the per-call timeout, and an optional `reasoning_effort` a reasoning model is asked to spend — leave the key out for a model that has no such setting. A working default ships with the repo; the API key is not stored here and comes from the environment. |
| `watcher.yaml` | `poll_seconds`, how often each project's source folder is looked at, and `quiet_seconds`, how long that folder must stop changing before the run reading it starts by itself. Set `WATCHER_CONFIG_PATH` to point at your own file instead. |
| `projects.yaml` | `projects_root`, the folder the Add-project box's dropdown lists the contents of. Ships as `sample-projects`, and must stay a relative path inside the repository — an absolute root is refused, because project creation refuses absolute folders and the dropdown would otherwise offer some. The system never creates a folder inside it or discovers a project by itself — a person puts a new client's folder there. |

Adding a rule, changing which formats are accepted, or changing how quickly the
watcher reacts, is an edit here, never a code change.

## Editing `watcher.yaml`

The shipped values are `poll_seconds: 2` and `quiet_seconds: 5`. Both must be
numbers above zero; anything else stops the application at startup and names
the key. In short: the folder is checked every 2 seconds, and a new file
starts a run once the folder has been quiet for 5 seconds.

- Files already in the folder when the application starts do not start a run
  — only a file that arrives afterwards does.
- One run at a time per project: files arriving during a run or a review wait
  for the next run.
- After a restart the watcher starts fresh, so files that arrived while it
  was down are read by the next run started by hand.

## Editing `rules.yaml`

Each rule needs a unique `id` and a `text`. Every rule the register is judged
against lives in this file; no rule is judged anywhere else.

A rule may also carry `applies_when` — a list of document kinds. A rule with
`applies_when` waits: it is not checked until the project has read at least
one document of every kind it lists. All four shipped rules use it:

    - id: R4
      text: "Every written requirement must have a testing outcome."
      applies_when:
        - testing feedback

R4 lists `testing feedback`, so it stays silent until a testing report
arrives. The four allowed values are `meeting notes`, `client requirements
document`, `handover summary`, `testing feedback`. A rule with no
`applies_when` is checked on every run.

A run reads this file once, when it starts, and keeps that copy for its whole
life. So:

- An edit applies to the next run, never to a run already under way or
  already finished.
- A run resumed after a crash still uses the rules it started with.

When the rules change, the next run examines the whole register again.
