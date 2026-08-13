from __future__ import annotations


class DocumentUnreadable(Exception):
    """A supported file this system will not read, and the reason why.

    The message is shown to the person who put the file in the folder, so it
    names both the cause and what to do about it.
    """
