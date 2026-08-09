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
from datetime import timedelta
from typing import ClassVar

from statement_normaliser.core import (
    normalise_symbol,
    parse_date,
    parse_money,
    parse_side,
    side_from_signed_quantity,
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

    def should_skip(self, row: dict[str, str]) -> bool:
        """Return True if this row is not a transaction and should be dropped.

        Statements carry rows that are structurally part of the file but are not
        trades: subtotals, page footers, continuation markers. They are not
        errors, so they must not surface as parse failures — and they must not
        become Transactions either.

        Defaults to False, because most formats contain only trades. Override in
        a parser whose source is known to emit something else.

        Args:
            row: The row as ``parse_row`` receives it — keys lower-cased.

        Returns:
            True to drop the row, False to parse it.
        """
        return False

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


class BrokerBParser(StatementParser):
    """Broker B: dates are DD/MM/YYYY, no fee column, BUY/SELL labels.

    Example header row::

        Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
    """

    name = "broker_b"
    required_headers = frozenset(
        {"date", "instrument", "b/s", "qty", "unit price", "currency"}
    )
    date_formats = ("%d/%m/%Y",)

    def parse_row(self, row: dict[str, str]) -> Transaction:
        """Convert one Broker A row into a canonical transaction."""
        return Transaction(
            trade_date=parse_date(row["date"], self.date_formats),
            symbol=normalise_symbol(row["instrument"]),
            side=parse_side(row["b/s"]),
            quantity=parse_money(row["qty"]),
            price=parse_money(row["unit price"]),
            fees=parse_money(row.get("commission") or "0"),
            currency=(row.get("currency") or "GBP").strip().upper(),
            source=self.name,
        )


class BrokerCParser(StatementParser):
    """Broker A: ISO dates, explicit fee column, BUY/SELL labels.

    Example header row::

        Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
    """

    name = "broker_c"
    required_headers = frozenset({"settle_dt", "sym", "quantity", "px", "fee"})
    date_formats = ("%d-%b-%Y",)

    def parse_row(self, row: dict[str, str]) -> Transaction:
        """Convert one Broker A row into a canonical transaction."""
        return Transaction(
            trade_date=parse_date(row["settle_dt"], self.date_formats)
            - timedelta(days=2),
            symbol=normalise_symbol(row["sym"]),
            side=side_from_signed_quantity(parse_money(row["quantity"])),
            quantity=abs(parse_money(row["quantity"])),
            price=parse_money(row["px"]),
            fees=parse_money(row.get("fee") or "0"),
            currency=(row.get("ccy") or "USD").strip().upper(),
            source=self.name,
        )


class BrokerDParser(StatementParser):
    """Broker A: ISO dates, explicit fee column, BUY/SELL labels.

    Example header row::

        Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
    """

    name = "broker_d"
    required_headers = frozenset(
        {"transaction date", "security", "type", "units", "gross amount"}
    )
    date_formats = ("%b %d, %Y",)

    def should_skip(self, row: dict[str, str]) -> bool:
        """Drop Broker D's trailing TOTAL summary row."""
        return row.get("transaction date", "").strip().upper() == "TOTAL"

    def parse_row(self, row: dict[str, str]) -> Transaction:
        """Convert one Broker A row into a canonical transaction."""
        return Transaction(
            trade_date=parse_date(row["transaction date"], self.date_formats),
            symbol=normalise_symbol(row["security"]),
            side=parse_side(row["type"]),
            quantity=parse_money(row["units"]),
            price=parse_money(row["gross amount"]) / parse_money(row["units"]),
            fees=parse_money(row.get("fee") or "0"),
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
PARSERS: tuple[type[StatementParser], ...] = (
    BrokerAParser,
    BrokerBParser,
    BrokerCParser,
    BrokerDParser,
)


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
