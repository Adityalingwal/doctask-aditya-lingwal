from __future__ import annotations


# The three weights of thing a run's `skipped` list holds, named in one place
# for the reason the statuses are: a reader scanning the tab must be able to
# tell a file an earlier run had already read from a file that was never read,
# and from a quote out of a file that *was* read and reached no row. Four
# modules write these entries.
READ_BEFORE_KIND = "read before"
NOT_READ_KIND = "not read"
NOT_ATTACHED_KIND = "not attached"
