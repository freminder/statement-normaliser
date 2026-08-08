"""All filesystem interaction. The only module allowed to touch disk.

Keeping I/O here means ``core.py`` and ``parsers.py`` stay testable with plain
Python literals — no temp files, no fixtures directory, no mocking. That is
worth the small amount of indirection it costs.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from dataclasses import fields
from pathlib import Path

from statement_normaliser.errors import RowParseError, UnknownFormatError
from statement_normaliser.models import Transaction
from statement_normaliser.parsers import select_parser

logger = logging.getLogger(__name__)

#: Column order of the canonical output. Derived from the dataclass so the two
#: cannot drift apart — add a field to Transaction and the CSV follows.
CANONICAL_HEADERS: tuple[str, ...] = tuple(f.name for f in fields(Transaction))


def read_statement(path: Path, *, strict: bool = True) -> Iterator[Transaction]:
    """Read one statement file and yield normalised transactions.

    Args:
        path: CSV file to read.
        strict: If True, the first unparsable row aborts with
            :class:`RowParseError`. If False, bad rows are logged and skipped.
            Default True: on a first run you want to *see* the mess, not
            silently drop 400 rows and reconcile to the wrong number.

    Yields:
        Transactions in file order.

    Raises:
        UnknownFormatError: If no parser recognises the header row.
        RowParseError: If a row fails to parse and ``strict`` is True.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []

        parser_cls = select_parser(list(headers))
        if parser_cls is None:
            raise UnknownFormatError(path, list(headers))

        parser = parser_cls()
        logger.info("parsing %s with %s", path.name, parser_cls.name)

        for line_number, raw_row in enumerate(reader, start=2):  # 1 is the header
            row = {
                (k or "").strip().lower(): (v or "").strip() for k, v in raw_row.items()
            }
            try:
                yield parser.parse_row(row)
            except (ValueError, KeyError) as exc:
                error = RowParseError(path, line_number, str(exc))
                if strict:
                    raise error from exc
                logger.warning("skipping row: %s", error)


def read_directory(directory: Path, *, strict: bool = True) -> list[Transaction]:
    """Read every CSV in a directory.

    Files are processed in sorted order so that a given input directory always
    produces byte-identical output. Reproducibility is not a luxury: it is what
    makes a diff between two runs meaningful.

    Args:
        directory: Folder containing statement CSVs.
        strict: Passed through to :func:`read_statement`.

    Returns:
        All transactions, sorted by trade date then symbol.

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"not a directory: {directory}")

    transactions: list[Transaction] = []
    for path in sorted(directory.glob("*.csv")):
        transactions.extend(read_statement(path, strict=strict))

    return sorted(transactions, key=lambda t: (t.trade_date, t.symbol))


def write_canonical(transactions: list[Transaction], path: Path) -> None:
    """Write transactions to the canonical CSV schema.

    Args:
        transactions: Rows to write, already in the order you want them.
        path: Destination. Parent directories are created if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(CANONICAL_HEADERS)
        for txn in transactions:
            writer.writerow([getattr(txn, header) for header in CANONICAL_HEADERS])

    logger.info("wrote %d transactions to %s", len(transactions), path)
