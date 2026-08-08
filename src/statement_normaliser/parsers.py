"""Per-broker parsers and the registry that dispatches between them.

# ─────────────────────────────────────────────────────────────────────────────
# THIS IS THE WORKED EXAMPLE. BrokerAParser is complete and tested.
# Brokers B, C and D are YOUR job. Match the standard set here.
# ─────────────────────────────────────────────────────────────────────────────

The shape to notice: a parser owns three things and nothing else — the headers
it recognises, the date formats its source uses, and how to turn one row into a
:class:`Transaction`. All the actual value parsing lives in ``core.py`` and is
shared. Adding broker five should mean adding one class and one test file, and
touching nothing that already works.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from statement_normaliser.core import (
    normalise_symbol,
    parse_date,
    parse_money,
    parse_side,
)
from statement_normaliser.models import Transaction


class StatementParser(ABC):
    """Base class for a single broker's statement format.

    Subclasses declare ``name``, ``required_headers`` and ``date_formats``,
    then implement :meth:`parse_row`.
    """

    name: ClassVar[str]
    required_headers: ClassVar[frozenset[str]]
    date_formats: ClassVar[tuple[str, ...]] = ("%Y-%m-%d",)

    @classmethod
    def matches(cls, headers: list[str]) -> bool:
        """Return True if this parser recognises a file's header row.

        Uses a subset test rather than equality: brokers add columns over time
        and we do not want a new "Notes" column to break ingestion of files
        that are otherwise identical.
        """
        present = {h.strip().lower() for h in headers}
        return cls.required_headers <= present

    @abstractmethod
    def parse_row(self, row: dict[str, str]) -> Transaction:
        """Convert one raw CSV row into a canonical transaction.

        Args:
            row: The row as produced by ``csv.DictReader``, keys lower-cased
                and stripped by the caller.

        Returns:
            The normalised transaction.

        Raises:
            ValueError: If any field is missing or unparsable. The caller
                wraps this in a ``RowParseError`` carrying the line number.
        """


class BrokerAParser(StatementParser):
    """Broker A: ISO dates, explicit fee column, BUY/SELL labels.

    The friendly case, included as the reference implementation.

    Example header row::

        Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
    """

    name = "broker_a"
    required_headers = frozenset({"trade date", "ticker", "action", "shares", "price"})
    date_formats = ("%Y-%m-%d",)

    def parse_row(self, row: dict[str, str]) -> Transaction:
        """Convert one Broker A row into a canonical transaction."""
        return Transaction(
            trade_date=parse_date(row["trade date"], self.date_formats),
            symbol=normalise_symbol(row["ticker"]),
            side=parse_side(row["action"]),
            quantity=parse_money(row["shares"]),
            price=parse_money(row["price"]),
            fees=parse_money(row.get("commission") or "0"),
            currency=(row.get("ccy") or "USD").strip().upper(),
            source=self.name,
        )


# ─── YOUR TURN ───────────────────────────────────────────────────────────────
#
# Implement these three. Each one is deliberately awkward in a different way,
# and each awkwardness is one you will genuinely meet on a client engagement.
#
# class BrokerBParser(StatementParser):
#     """Broker B: DD/MM/YYYY dates, no fee column, B/S labels, £ symbols."""
#     # Ambiguity to resolve: is 03/04/2024 March or April? Your date_formats
#     # declaration is the answer. Write down why in DECISIONS.md.
#
# class BrokerCParser(StatementParser):
#     """Broker C: signed quantities (negative = sell), no Action column."""
#     # The canonical model keeps quantity positive and direction in `side`.
#     # Derive the side from the sign, then take abs(). Test the zero case.
#
# class BrokerDParser(StatementParser):
#     """Broker D: a TOTAL summary row at the bottom, fees bundled into price."""
#     # A parser cannot skip rows on its own — it only sees one at a time.
#     # Decide where the skip belongs: a `should_skip(row)` hook on the base
#     # class, or a filter in io.py? Both are defensible. Pick one, justify it.
#
# ─────────────────────────────────────────────────────────────────────────────


#: Registration order matters when two formats could both match. Most specific
#: first. Add your parsers here as you write them.
PARSERS: tuple[type[StatementParser], ...] = (BrokerAParser,)


def select_parser(headers: list[str]) -> type[StatementParser] | None:
    """Find the first registered parser that recognises these headers.

    Args:
        headers: The file's header row, as read.

    Returns:
        The matching parser class, or ``None`` if nothing matched. Returning
        ``None`` rather than raising keeps this function pure and lets the
        caller — which knows the file path — raise a useful error.
    """
    for parser in PARSERS:
        if parser.matches(headers):
            return parser
    return None
