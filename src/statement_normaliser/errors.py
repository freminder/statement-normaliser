"""Exception hierarchy for the statement normaliser.

One base class so callers can catch everything this package raises with a
single ``except NormaliserError``, and specific subclasses so they can be
selective when they need to be.

Every message names *the thing that broke and where it was*. An error that
says "invalid date" costs someone twenty minutes; one that says
"invalid date '15.01.24' in broker_a.csv line 47" costs them twenty seconds.
"""

from __future__ import annotations

from pathlib import Path


class NormaliserError(Exception):
    """Base class for every error raised by this package."""


class UnknownFormatError(NormaliserError):
    """No registered parser recognised a file's header row."""

    def __init__(self, path: Path, headers: list[str]) -> None:
        """Store the offending path and headers alongside the message."""
        super().__init__(f"no parser matched headers {headers!r} in {path}")
        self.path = path
        self.headers = headers


class RowParseError(NormaliserError):
    """A single row could not be parsed.

    Carries the line number so the operator can open the file and look at it.
    """

    def __init__(self, path: Path, line_number: int, reason: str) -> None:
        """Store the location so a caller can report or re-raise it usefully."""
        super().__init__(f"{path}:{line_number}: {reason}")
        self.path = path
        self.line_number = line_number
        self.reason = reason
