"""Tests for the canonical Transaction model and its invariants."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from statement_normaliser.models import Side, Transaction


def make_txn(**overrides: object) -> Transaction:
    """Build a valid transaction, overriding only what a test cares about.

    A factory like this keeps tests readable: the reader sees exactly the one
    field under test rather than eight lines of irrelevant setup.
    """
    defaults: dict[str, object] = {
        "trade_date": date(2024, 1, 15),
        "symbol": "AAPL",
        "side": Side.BUY,
        "quantity": Decimal("100"),
        "price": Decimal("150.00"),
        "fees": Decimal("1.50"),
        "currency": "USD",
        "source": "test",
    }
    return Transaction(**{**defaults, **overrides})  # type: ignore[arg-type]


def test_buy_reduces_cash_by_value_plus_fees() -> None:
    txn = make_txn(side=Side.BUY)
    assert txn.net_value == Decimal("-15001.50")


def test_sell_increases_cash_by_value_minus_fees() -> None:
    txn = make_txn(side=Side.SELL)
    assert txn.net_value == Decimal("14998.50")


@pytest.mark.parametrize("bad_quantity", [Decimal("0"), Decimal("-1")])
def test_rejects_non_positive_quantity(bad_quantity: Decimal) -> None:
    """Direction belongs in `side`, never in the sign of the quantity.

    Broker C reports sells as negative quantities. Enforcing positivity here
    forces that translation to happen in the parser, where it is visible and
    tested, rather than leaking a second representation through the codebase.
    """
    with pytest.raises(ValueError, match="quantity must be positive"):
        make_txn(quantity=bad_quantity)


def test_rejects_negative_fees() -> None:
    with pytest.raises(ValueError, match="fees cannot be negative"):
        make_txn(fees=Decimal("-1"))


def test_transaction_is_immutable() -> None:
    """Frozen so a downstream bug cannot rewrite history in place."""
    txn = make_txn()
    with pytest.raises(AttributeError):
        txn.symbol = "MSFT"  # type: ignore[misc]
