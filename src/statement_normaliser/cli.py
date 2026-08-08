"""Command-line entry point.

Deliberately thin. The CLI parses arguments, configures logging and calls into
the library — it contains no business logic at all. That separation is what
lets you import this package from a notebook, a test or a web service later
without dragging argparse along.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from statement_normaliser.errors import NormaliserError
from statement_normaliser.io import read_directory, write_canonical


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Split out from :func:`main` so the CLI contract can be unit tested without
    running the program.
    """
    parser = argparse.ArgumentParser(
        prog="normalise",
        description="Normalise broker statement CSVs into one canonical schema.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="directory containing broker statement CSVs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="path to write the canonical CSV",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="log and skip unparsable rows instead of failing (default: fail)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse and report, but write nothing",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Argument list, defaulting to ``sys.argv[1:]``. Injectable so
            tests can drive the CLI directly.

    Returns:
        A process exit code: 0 on success, 1 on a handled error. Exit codes
        are an interface — anything scripting this tool depends on them.
    """
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        transactions = read_directory(args.input, strict=not args.lenient)
    except (NormaliserError, FileNotFoundError) as exc:
        logging.error("%s", exc)
        return 1

    if args.dry_run:
        logging.info(
            "dry run: parsed %d transactions, wrote nothing", len(transactions)
        )
        return 0

    write_canonical(transactions, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
