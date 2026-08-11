# config

Everything that should be changeable without touching code lives here.

| File | Holds |
|---|---|
| `rules.yaml` _(to be added)_ | The rules the system checks documents and the register against. A default set ships with the repo so a fresh clone runs; point at your own file to replace it. |
| `formats.yaml` _(to be added)_ | The accepted file-format extensions (`.pdf`, `.docx`, `.md`, `.txt`). Removing a line disables that format; adding one only works if a reader for it exists in `app/ingest/` — a startup check says so if not. |

Adding a rule, or changing which formats are accepted, is an edit here, never
a code change.
