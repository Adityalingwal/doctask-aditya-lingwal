# Demo runs — dev server only

The review screen shows only what the application answers for a run. Until a
real run exists, there is nothing to design against, so the Vite dev server
answers the same six endpoints here with runs that cover every state the screen
has to render: waiting for review, mid-stage, failed, skipped documents, the
rules-only route, and an exported register.

Open <http://localhost:5173/demo> for the list.

## What is real and what is not

The response shapes come from `../tests/server_replies.js`, which follows
`app/runs/run_status.py` and `app/register/export_register.py`. The **values**
are invented; the **shapes** are the application's. A demo run is never a claim
about a real run — every figure in it, including its timings and its estimated
cost, is made up for the screen.

## Removing it

Nothing under `ui/src/` imports this folder, so removal is two steps:

1. Delete `ui/demo/`.
2. Remove `serveDemoRuns()` and its import from `ui/vite.config.js`.

The screen then talks only to the application, which is what it does in a build
already: the plugin declares `apply: "serve"`, so no line of this folder enters
`vite build` or the bundle FastAPI serves at `/ui`.
