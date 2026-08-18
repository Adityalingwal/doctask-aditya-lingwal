# sample-projects

Every project's own folder of source documents lives here — one folder per
project, a single run consuming one batch from that folder, not the whole
thing at once; one project yields many batches over time.

This folder starts **empty**. The application never creates a project of its
own; a project exists only once an operator creates one by hand, over a
folder that already sits directly inside `sample-projects/`, through the
screen's Add-project box or the MCP `create_project` tool.

## The Helpline AI corpus

The current sample documents are `sample-documents/helpline-ai/` — see
[`sample-documents/helpline-ai/README.md`](../sample-documents/helpline-ai/README.md)
for what the corpus is, what it proves, and the staged procedure for copying
it in. Those documents are staged by hand into a folder created here, in
batches, rather than committed as a project of their own — that is what lets
the watcher fire once per batch instead of once over a whole dump. Documents
staged under `sample-projects/helpline-ai/` are git-ignored.
