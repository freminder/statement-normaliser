"""Core data structures for the statement normaliser.

Everything in this module is immutable and validates itself on construction.
Pushing validation into the type means the rest of the codebase can assume a
``Transaction`` is well-formed, rather than re-checking at every call site.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Side(StrEnum):
    """Direction of a trade.

    A string enum (rather than a bare ``str``) so that typos fail at the
    boundary instead of silently producing an unmatched filter later.
    """

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Transaction:
    """A single normalised trade, in the canonical schema.

    Money is ``Decimal`` throughout. Broker statements are exact to the cent,
    and binary floats are not: ``0.1 + 0.2 != 0.3``. Over a few thousand rows
    that drift becomes a reconciliation break, which in a regulated firm is an
    incident rather than a rounding error. See ``tests/test_models.py``.

    Attributes:
        trade_date: Date the trade executed. Not settlement date — sources
            disagree on this and we normalise to trade date. See DECISIONS.md.
        symbol: Ticker, upper-cased and stripped.
        side: BUY or SELL.
        quantity: Units traded. Always positive; direction lives in ``side``,
            never in the sign of the quantity.
        price: Price per unit in ``currency``.
        fees: Commission and taxes. Zero if the source does not report them.
        currency: ISO 4217 code.
        source: Which broker file this row came from, for audit.

    Raises:
        ValueError: If quantity or price is not positive, or fees are negative.
    """

    trade_date: date
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
    fees: Decimal
    currency: str
    source: str

    def __post_init__(self) -> None:
        """Enforce the invariants at construction time.

        Validating here means no other code has to. Every ``Transaction`` that
        exists anywhere in the program is, by construction, valid.
        """
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.price <= 0:
            raise ValueError(f"price must be positive, got {self.price}")
        if self.fees < 0:
            raise ValueError(f"fees cannot be negative, got {self.fees}")

    @property
    def gross_value(self) -> Decimal:
        """Trade value before fees."""
        return self.quantity * self.price

    @property
    def net_value(self) -> Decimal:
        """Cash impact of the trade, signed from the account's perspective.

        Negative for a buy (cash leaves), positive for a sell (cash arrives).
        Fees always reduce the account either way.
        """
        if self.side is Side.BUY:
            return -(self.gross_value + self.fees)
        return self.gross_value - self.fees
