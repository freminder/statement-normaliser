"""Tests for pure parsing logic.

Note the shape of these tests, because it is the shape all twelve projects
should use:

* Test names are sentences describing a behaviour, not ``test_parse_1``.
* Edge cases outnumber happy paths. The happy path is the least likely thing
  to break in production.
* ``parametrize`` instead of copy-pasted near-identical tests.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from statement_normaliser.core import (
    normalise_symbol,
    parse_date,
    parse_money,
    parse_side,
)
from statement_normaliser.models import Side


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2024-01-15", date(2024, 1, 15)),
        ("15/01/2024", date(2024, 1, 15)),
        ("15-Jan-2024", date(2024, 1, 15)),
        ("Jan 15, 2024", date(2024, 1, 15)),
        ("  2024-01-15  ", date(2024, 1, 15)),  # statements are full of padding
    ],
)
def test_parses_each_known_date_format(raw: str, expected: date) -> None:
    assert parse_date(raw) == expected


def test_rejects_unknown_date_format_with_a_useful_message() -> None:
    with pytest.raises(ValueError, match="unrecognised date"):
        parse_date("15.01.24")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234.50", Decimal("1234.50")),
        ("$1,234.50", Decimal("1234.50")),
        ("£1,234.50", Decimal("1234.50")),
        ("(45.00)", Decimal("-45.00")),  # accounting-style negative
        ("0.01", Decimal("0.01")),
    ],
)
def test_parses_monetary_values(raw: str, expected: Decimal) -> None:
    assert parse_money(raw) == expected


def test_money_parsing_is_exact_not_approximate() -> None:
    """The reason money is Decimal and not float.

    This test is the argument. Run it, then change parse_money to return
    float(cleaned) and watch it fail. That failure is a reconciliation break
    in production, and this is the interview answer to "why Decimal?".
    """
    total = parse_money("0.10") + parse_money("0.20")
    assert total == Decimal("0.30")
    assert float("0.10") + float("0.20") != float("0.30")  # the float bug itself


@pytest.mark.parametrize("raw", ["", "   ", "abc", "$"])
def test_rejects_non_numeric_money(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_money(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BUY", Side.BUY),
        ("b", Side.BUY),
        ("Bought", Side.BUY),
        ("SLD", Side.SELL),
        ("  sale  ", Side.SELL),
    ],
)
def test_maps_broker_side_labels_to_canonical(raw: str, expected: Side) -> None:
    assert parse_side(raw) == expected


def test_rejects_unknown_side_label() -> None:
    with pytest.raises(ValueError, match="unrecognised side"):
        parse_side("TRANSFER")


def test_normalise_symbol_preserves_exchange_suffix() -> None:
    """VOD and VOD.L may be different instruments. Do not silently merge them."""
    assert normalise_symbol(" vod.l ") == "VOD.L"
    assert normalise_symbol("vod") == "VOD"
