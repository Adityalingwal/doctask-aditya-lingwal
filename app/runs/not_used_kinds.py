from __future__ import annotations


# The three weights of thing a run's `not_used` list holds, named in one place
# for the reason the statuses are: a reader scanning the tab must be able to
# tell a file an earlier run had already read from a requirement that fell out
# of the register, and four modules write these entries.
ALREADY_READ_KIND = "already read"
NOT_READ_KIND = "not read"
DROPPED_KIND = "dropped"
