"""Normalise broker statement CSVs into a single canonical schema.

Public surface:
    >>> from statement_normaliser import Transaction, read_directory
"""

from statement_normaliser.errors import (
    NormaliserError,
    RowParseError,
    UnknownFormatError,
)
from statement_normaliser.io import read_directory, read_statement, write_canonical
from statement_normaliser.models import Side, Transaction

__all__ = [
    "NormaliserError",
    "RowParseError",
    "Side",
    "Transaction",
    "UnknownFormatError",
    "read_directory",
    "read_statement",
    "write_canonical",
]
__version__ = "0.1.0"
