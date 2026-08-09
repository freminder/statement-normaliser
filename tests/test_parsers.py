"""Tests for the per-broker parsers and the dispatch registry.

Every parser needs the same four groups:

1. ``matches()`` recognises its own header row and rejects others
2. ``parse_row()`` maps a row onto a correct canonical Transaction
3. ``should_skip()`` drops non-transaction rows — and only those
4. ``select_parser()`` finds it in the registry

Two rules the tests below follow, and both matter more than coverage:

**Fixtures are copied from examples/, never invented.** A fixture is the test's
claim about what the source actually sends. Make it up and you test your
imagination. Every literal here appears verbatim in a committed CSV.

**Assertions use canonical field names.** ``trade_date``, ``symbol``, ``side``,
``quantity``, ``price``, ``fees``, ``currency``. Never the source's names. If a
test could tell which broker a Transaction came from by its field names,
normalisation has failed.

Row dict keys are lower-cased because that is what ``io.read_statement`` does
before calling ``parse_row``. Test the input your code really receives.

Assertions marked DECISION encode a judgement recorded in DECISIONS.md. If you
change the decision, this test must change with it — that is deliberate.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from statement_normaliser.models import Side
from statement_normaliser.parsers import (
    BrokerAParser,
    BrokerBParser,
    BrokerCParser,
    BrokerDParser,
    StatementParser,
    select_parser,
)

# ─── Header rows, verbatim from examples/ ────────────────────────────────────

BROKER_A_HEADERS = [
    "Trade Date",
    "Ticker",
    "Action",
    "Shares",
    "Price",
    "Commission",
    "Ccy",
]
BROKER_B_HEADERS = ["Date", "Instrument", "B/S", "Qty", "Unit Price", "Currency"]
BROKER_C_HEADERS = ["SETTLE_DT", "SYM", "QUANTITY", "PX", "FEE"]
BROKER_D_HEADERS = ["Transaction Date", "Security", "Type", "Units", "Gross Amount"]


# ─── Row factories ───────────────────────────────────────────────────────────
# Each mirrors one real line of the matching CSV, with keys lower-cased exactly
# as io.read_statement produces them. Override one field per test so the reader
# sees the single thing under test rather than seven lines of setup.


def broker_a_row(**overrides: str) -> dict[str, str]:
    """Row 1 of examples/broker_a.csv."""
    return {
        "trade date": "2024-01-15",
        "ticker": "AAPL",
        "action": "BUY",
        "shares": "100",
        "price": "150.00",
        "commission": "1.50",
        "ccy": "USD",
    } | overrides


def broker_b_row(**overrides: str) -> dict[str, str]:
    """Row 1 of examples/broker_b.csv — quoted thousands, GBP, B/S label."""
    return {
        "date": "15/01/2024",
        "instrument": "VOD.L",
        "b/s": "B",
        "qty": "1,000",
        "unit price": "£0.69",
        "currency": "GBP",
    } | overrides


def broker_c_row(**overrides: str) -> dict[str, str]:
    """Row 1 of examples/broker_c.csv — positive quantity, no side column."""
    return {
        "settle_dt": "17-Jan-2024",
        "sym": "AAPL",
        "quantity": "200",
        "px": "149.10",
        "fee": "2.95",
    } | overrides


def broker_d_row(**overrides: str) -> dict[str, str]:
    """Row 1 of examples/broker_d.csv — gross amount, no price, no fee column."""
    return {
        "transaction date": "Jan 15, 2024",
        "security": "AMZN",
        "type": "Purchase",
        "units": "10",
        "gross amount": "$1,552.40",
    } | overrides


#: Every parser paired with the header row it owns. One list, so a fifth broker
#: is added in exactly one place and every parametrized test picks it up.
PARSER_HEADERS: list[tuple[type[StatementParser], list[str]]] = [
    (BrokerAParser, BROKER_A_HEADERS),
    (BrokerBParser, BROKER_B_HEADERS),
    (BrokerCParser, BROKER_C_HEADERS),
    (BrokerDParser, BROKER_D_HEADERS),
]

ALL_PARSERS = [pytest.param(p, h, id=p.name) for p, h in PARSER_HEADERS]


# ─── 1. Header matching ──────────────────────────────────────────────────────
# Parametrized rather than four asserts in one test: a failure names the broker,
# and one broker breaking does not hide the other three.


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_matches_its_own_header_row(parser: type[StatementParser], headers: list[str]):
    assert parser.matches(headers)


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_matching_is_case_insensitive(
    parser: type[StatementParser], headers: list[str]
):
    assert parser.matches([h.upper() for h in headers])
    assert parser.matches([h.lower() for h in headers])


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_matching_survives_an_extra_column(
    parser: type[StatementParser], headers: list[str]
):
    """Brokers add columns over time; a new one must not break ingestion.

    This is why ``matches`` uses a subset test rather than equality.
    """
    assert parser.matches([*headers, "Notes"])


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_matches_no_other_brokers_headers(
    parser: type[StatementParser], headers: list[str]
):
    """Each parser must reject all three of the others.

    Overlapping matches would make dispatch depend on registration order, which
    is a bug waiting for the day someone reorders the tuple.
    """
    for other, other_headers in PARSER_HEADERS:
        if other is parser:
            continue
        assert not parser.matches(other_headers), (
            f"{parser.name} also matched {other.name}"
        )


# ─── 2. Broker A — explicit columns, the easy case ───────────────────────────


def test_broker_a_parses_every_field():
    """Assert the whole Transaction, not just the field you were thinking about.

    A parser that gets the date right and silently drops the currency passes a
    narrow test and fails in production.
    """
    txn = BrokerAParser().parse_row(broker_a_row())

    assert txn.trade_date == date(2024, 1, 15)
    assert txn.symbol == "AAPL"
    assert txn.side is Side.BUY
    assert txn.quantity == Decimal("100")
    assert txn.price == Decimal("150.00")
    assert txn.fees == Decimal("1.50")
    assert txn.currency == "USD"
    assert txn.source == "broker_a"


def test_broker_a_parses_a_sell():
    assert BrokerAParser().parse_row(broker_a_row(action="SELL")).side is Side.SELL


# ─── 2. Broker B — DD/MM dates, £ prices, quoted thousands, B/S, no fees ─────


def test_broker_b_parses_every_field():
    txn = BrokerBParser().parse_row(broker_b_row())

    assert txn.trade_date == date(2024, 1, 15)
    assert txn.symbol == "VOD.L"
    assert txn.side is Side.BUY
    assert txn.quantity == Decimal("1000")
    assert txn.price == Decimal("0.69")
    assert txn.fees == Decimal("0")
    assert txn.currency == "GBP"
    assert txn.source == "broker_b"


def test_broker_b_strips_thousands_separator():
    """'1,000' is one thousand, not one hundred. The comma hides the bug."""
    txn = BrokerBParser().parse_row(broker_b_row(qty="1,000"))

    assert txn.quantity == Decimal("1000")


def test_broker_b_strips_currency_symbol():
    txn = BrokerBParser().parse_row(broker_b_row(**{"unit price": "£4.82"}))

    assert txn.price == Decimal("4.82")


@pytest.mark.parametrize(("label", "expected"), [("B", Side.BUY), ("S", Side.SELL)])
def test_broker_b_maps_single_letter_sides(label: str, expected: Side):
    assert BrokerBParser().parse_row(broker_b_row(**{"b/s": label})).side is expected


def test_broker_b_reads_day_first_dates():
    """DECISION #4 — Broker B reports DD/MM/YYYY.

    03/04/2024 is 3 April, not 3 March. This assertion is the enforcement of
    that decision: change date_formats to %m/%d/%Y and this test goes red,
    which is exactly what should happen.
    """
    txn = BrokerBParser().parse_row(broker_b_row(date="03/04/2024"))

    assert txn.trade_date == date(2024, 4, 3)


def test_broker_b_keeps_the_exchange_suffix():
    """DECISION #5 — VOD and VOD.L are different instruments.

    Different exchange, different currency, different ADR ratio. Merging them
    would corrupt position counts silently.
    """
    assert BrokerBParser().parse_row(broker_b_row(instrument="vod.l")).symbol == "VOD.L"


def test_broker_b_reports_zero_fees():
    """DECISION — Broker B has no fee column at all.

    Zero here means 'not reported', not 'none charged'. The canonical schema
    cannot express unknown, so zero is the least-wrong option available.
    """
    assert BrokerBParser().parse_row(broker_b_row()).fees == Decimal("0")


# ─── 2. Broker C — signed quantities, no side column ─────────────────────────


def test_broker_c_parses_every_field():
    txn = BrokerCParser().parse_row(broker_c_row())

    assert txn.symbol == "AAPL"
    assert txn.side is Side.BUY
    assert txn.quantity == Decimal("200")
    assert txn.price == Decimal("149.10")
    assert txn.fees == Decimal("2.95")
    assert txn.source == "broker_c"


def test_broker_c_negative_quantity_is_a_sell_with_positive_quantity():
    """The canonical rule: direction lives in ``side``, never in a sign.

    Row 2 of the CSV reports -75. It must become SELL 75, not SELL -75 and not
    BUY -75. This is the single most important assertion for this parser.
    """
    txn = BrokerCParser().parse_row(broker_c_row(quantity="-75"))

    assert txn.side is Side.SELL
    assert txn.quantity == Decimal("75")


def test_broker_c_positive_quantity_is_a_buy():
    txn = BrokerCParser().parse_row(broker_c_row(quantity="50"))

    assert txn.side is Side.BUY
    assert txn.quantity == Decimal("50")


def test_broker_c_zero_quantity_is_rejected():
    """DECISION — zero has no direction, so the row cannot be interpreted.

    Skipping it silently or defaulting to BUY would both invent information.
    """
    with pytest.raises(ValueError):
        BrokerCParser().parse_row(broker_c_row(quantity="0"))


# ─── 2. Broker D — gross amount, derived price, no fees, summary row ─────────


def test_broker_d_parses_every_field():
    txn = BrokerDParser().parse_row(broker_d_row())

    assert txn.trade_date == date(2024, 1, 15)
    assert txn.symbol == "AMZN"
    assert txn.side is Side.BUY
    assert txn.quantity == Decimal("10")
    assert txn.currency == "USD"
    assert txn.source == "broker_d"


def test_broker_d_derives_price_from_gross_and_units():
    """Broker D reports no price. $1,552.40 over 10 units is 155.24 each."""
    assert BrokerDParser().parse_row(broker_d_row()).price == Decimal("155.24")


def test_broker_d_price_round_trips_to_the_reported_gross():
    """The derived price, multiplied back out, must equal what Broker D said.

    This is the check that makes derivation safe: if rounding ever breaks the
    round trip, the numbers stop reconciling against the source and this fails.
    """
    txn = BrokerDParser().parse_row(broker_d_row())

    assert txn.gross_value == Decimal("1552.40")


@pytest.mark.parametrize(
    ("label", "expected"), [("Purchase", Side.BUY), ("Sale", Side.SELL)]
)
def test_broker_d_maps_word_sides(label: str, expected: Side):
    assert BrokerDParser().parse_row(broker_d_row(type=label)).side is expected


def test_broker_d_reports_zero_fees():
    """DECISION — fees are bundled into the gross amount and not reported.

    Zero means 'not separately reported'. The derived price is therefore
    fee-inflated: it reconciles to the source, but it is not a clean execution
    price. See DECISIONS.md.
    """
    assert BrokerDParser().parse_row(broker_d_row()).fees == Decimal("0")


# ─── 3. Skipping non-transaction rows ────────────────────────────────────────


def test_broker_d_skips_the_total_row():
    """The trailing TOTAL row is a summary, not a trade."""
    total_row = {
        "transaction date": "TOTAL",
        "security": "",
        "type": "",
        "units": "23",
        "gross amount": "$3,986.55",
    }

    assert BrokerDParser().should_skip(total_row)


def test_broker_d_does_not_skip_a_real_row():
    """The dangerous direction. An over-eager skip deletes trades silently.

    A false positive here produces no error, no warning and a short file.
    """
    assert not BrokerDParser().should_skip(broker_d_row())


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_parsers_skip_nothing_by_default(
    parser: type[StatementParser], headers: list[str]
):
    """Only Broker D overrides should_skip; the rest must pass every row."""
    if parser is BrokerDParser:
        pytest.skip("Broker D deliberately overrides should_skip")
    assert not parser().should_skip({"anything": "at all"})


# ─── 4. Registry dispatch ────────────────────────────────────────────────────
# A perfect parser that never gets selected is a parser that does not exist.


@pytest.mark.parametrize(("parser", "headers"), ALL_PARSERS)
def test_registry_selects_the_right_parser(
    parser: type[StatementParser], headers: list[str]
):
    assert select_parser(headers) is parser


def test_registry_returns_none_for_unknown_headers():
    """None rather than an exception: this function stays pure.

    The caller knows the file path and can raise an error worth reading.
    """
    assert select_parser(["foo", "bar"]) is None


def test_registry_returns_none_for_empty_headers():
    assert select_parser([]) is None
