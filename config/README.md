# config

Everything that should be changeable without touching code lives here.

| File | Holds |
|---|---|
| `rules.yaml` | The rules the register is judged against in Examine. A default set ships with the repo so a fresh clone runs; set `RULES_CONFIG_PATH` to point at your own file instead. |
| `formats.yaml` | The accepted file-format extensions (`.pdf`, `.docx`, `.md`, `.txt`) and the document page limit. Removing a format disables it; adding one only works if a reader for it exists in `app/ingest/` — a startup check says so if not. |
| `model.yaml` | The OpenRouter model name, base URL, and per-token rates. Its `call:` block holds the model-call attempt count and per-call timeout. A working default ships with the repo; the API key is not stored here and comes from the environment. |

Adding a rule, or changing which formats are accepted, is an edit here, never
a code change.

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
