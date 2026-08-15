from __future__ import annotations


class Refused(Exception):
    """A core refusal: one message naming both the cause and the practical fix.

    Core raises these so that every door — HTTP today, MCP beside it — reports
    the same refusal for the same call. A door chooses how to carry it, never
    what it says.
    """


class UnknownId(Refused):
    """The caller named a project, run or decision that does not exist."""


class NotPossibleNow(Refused):
    """The run's own state forbids what was asked of it."""


class UnusableRequest(Refused):
    """What the caller asked for is not something this system accepts."""


class RunsUnavailable(Refused):
    """No run can start, because the model client could not be built."""


class ProjectsUnavailable(Refused):
    """The project list cannot be read, because config/projects.yaml is
    missing, unreadable, or names a root that does not exist."""
