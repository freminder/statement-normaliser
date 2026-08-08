"""Tests for the command-line entry point.

The CLI is an interface with a contract: flags, and exit codes. Anything that
scripts this tool depends on both, so both get tested. This is why ``main()``
takes ``argv`` as an argument instead of reading ``sys.argv`` directly —
injectable arguments make the entry point testable without subprocesses.
"""

from __future__ import annotations

from pathlib import Path

from statement_normaliser.cli import main

BROKER_A_CSV = """Trade Date,Ticker,Action,Shares,Price,Commission,Ccy
2024-01-15,AAPL,BUY,100,150.00,1.50,USD
"""


def test_writes_output_and_exits_zero(tmp_path: Path) -> None:
    (tmp_path / "broker_a.csv").write_text(BROKER_A_CSV, encoding="utf-8")
    out = tmp_path / "canonical.csv"

    exit_code = main(["--input", str(tmp_path), "--output", str(out)])

    assert exit_code == 0
    assert out.exists()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    (tmp_path / "broker_a.csv").write_text(BROKER_A_CSV, encoding="utf-8")
    out = tmp_path / "canonical.csv"

    exit_code = main(["--input", str(tmp_path), "--output", str(out), "--dry-run"])

    assert exit_code == 0
    assert not out.exists()


def test_missing_input_directory_exits_one(tmp_path: Path) -> None:
    """A non-zero exit code is the only thing a shell script can see."""
    exit_code = main(
        ["--input", str(tmp_path / "nope"), "--output", str(tmp_path / "o.csv")]
    )

    assert exit_code == 1


def test_unrecognised_format_exits_one_without_traceback(tmp_path: Path) -> None:
    (tmp_path / "mystery.csv").write_text("foo,bar\n1,2\n", encoding="utf-8")

    exit_code = main(["--input", str(tmp_path), "--output", str(tmp_path / "o.csv")])

    assert exit_code == 1
