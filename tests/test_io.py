"""Tests for the I/O layer, using pytest's tmp_path rather than real files."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from statement_normaliser.errors import RowParseError, UnknownFormatError
from statement_normaliser.io import read_directory, read_statement, write_canonical
from statement_normaliser.models import Side

BROKER_A_CSV = """Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
2024-01-15,AAPL,BUY,100,150.00,1.50,USD
2024-02-20,MSFT,SELL,50,410.25,1.50,USD
"""


def write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_reads_a_well_formed_broker_a_statement(tmp_path: Path) -> None:
    path = write(tmp_path, "broker_a.csv", BROKER_A_CSV)

    transactions = list(read_statement(path))

    assert len(transactions) == 2
    assert transactions[0].symbol == "AAPL"
    assert transactions[0].side is Side.BUY
    assert transactions[1].price == Decimal("410.25")


def test_unknown_headers_raise_naming_the_file(tmp_path: Path) -> None:
    path = write(tmp_path, "mystery.csv", "foo,bar\n1,2\n")

    with pytest.raises(UnknownFormatError) as excinfo:
        list(read_statement(path))

    assert "mystery.csv" in str(excinfo.value)


def test_bad_row_reports_the_line_number(tmp_path: Path) -> None:
    """Errors must name the line number.

    The difference between naming it and not is twenty seconds versus twenty
    minutes of someone's afternoon.
    """
    broken = BROKER_A_CSV + "not-a-date,GOOG,BUY,10,100.00,1.00,USD\n"
    path = write(tmp_path, "broker_a.csv", broken)

    with pytest.raises(RowParseError) as excinfo:
        list(read_statement(path))

    assert excinfo.value.line_number == 4


def test_lenient_mode_skips_bad_rows(tmp_path: Path) -> None:
    broken = BROKER_A_CSV + "not-a-date,GOOG,BUY,10,100.00,1.00,USD\n"
    path = write(tmp_path, "broker_a.csv", broken)

    transactions = list(read_statement(path, strict=False))

    assert len(transactions) == 2


def test_directory_output_is_deterministic(tmp_path: Path) -> None:
    """Same input directory must always produce the same output ordering.

    Without this, a diff between two runs is meaningless, and meaningless
    diffs are how regressions get shipped.
    """
    write(tmp_path, "b.csv", BROKER_A_CSV)
    write(tmp_path, "a.csv", BROKER_A_CSV)

    first = read_directory(tmp_path)
    second = read_directory(tmp_path)

    assert first == second
    assert [t.trade_date for t in first] == sorted(t.trade_date for t in first)


def test_round_trip_writes_a_readable_canonical_file(tmp_path: Path) -> None:
    write(tmp_path, "broker_a.csv", BROKER_A_CSV)
    out = tmp_path / "out" / "canonical.csv"

    write_canonical(read_directory(tmp_path), out)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("trade_date,symbol,side")
    assert len(lines) == 3  # header + 2 data rows


def test_missing_directory_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not a directory"):
        read_directory(tmp_path / "nope")
