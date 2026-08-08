"""Pure business logic: parsing values and normalising rows.

Nothing in this module touches the filesystem, the network or the clock. That
is deliberate and it is the single most important structural rule in the
project — it means every function here is testable with a literal, and the
awkward parts (I/O, ordering, encoding) stay isolated in ``io.py``.

If you find yourself wanting to ``open()`` something here, the design has
drifted. Pass the data in instead.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from statement_normaliser.models import Side

# Ordered most-specific first. ``%d/%m/%Y`` and ``%m/%d/%Y`` are genuinely
# ambiguous for days 1-12, which is why each parser declares the formats its
# own source uses rather than us guessing globally. See DECISIONS.md #2.
_DEFAULT_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%b-%Y",
    "%b %d, %Y",
)


def parse_date(raw: str, formats: tuple[str, ...] = _DEFAULT_DATE_FORMATS) -> date:
    """Parse a date string, trying each format in order.

    Args:
        raw: The raw cell value. Surrounding whitespace is tolerated.
        formats: ``strptime`` formats to attempt, most specific first.

    Returns:
        The parsed date.

    Raises:
        ValueError: If no format matched. The message lists what was tried,
            so the fix is usually obvious from the error alone.

    Example:
        >>> parse_date("2024-01-15")
        datetime.date(2024, 1, 15)
    """
    cleaned = raw.strip()
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date {cleaned!r}; tried {list(formats)}")


def parse_money(raw: str) -> Decimal:
    """Parse a monetary cell into an exact ``Decimal``.

    Handles the usual statement noise: currency symbols, thousands separators,
    and accounting-style negatives in parentheses.

    Args:
        raw: The raw cell value, e.g. ``"$1,234.50"`` or ``"(45.00)"``.

    Returns:
        An exact Decimal. Constructed from a *string*, never from a float —
        ``Decimal(0.1)`` has already lost the precision before Decimal sees it.

    Raises:
        ValueError: If the cleaned value is not a number.

    Example:
        >>> parse_money("$1,234.50")
        Decimal('1234.50')
        >>> parse_money("(45.00)")
        Decimal('-45.00')
    """
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("empty monetary value")

    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]

    for junk in ("$", "£", "€", ",", " "):
        cleaned = cleaned.replace(junk, "")

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {raw!r}") from exc

    return -value if negative else value


def parse_side(raw: str) -> Side:
    """Map a source-specific side label onto the canonical :class:`Side`.

    Brokers use every variant imaginable: ``B``/``S``, ``BOT``/``SLD``,
    ``Purchase``/``Sale``. Extending this mapping is cheaper and far easier to
    test than scattering ``if raw == "BOT"`` through the parsers.

    Args:
        raw: Source label, any case.

    Returns:
        The canonical side.

    Raises:
        ValueError: If the label is not recognised.
    """
    normalised = raw.strip().upper()
    buys = {"B", "BUY", "BOT", "BOUGHT", "PURCHASE", "DEBIT"}
    sells = {"S", "SELL", "SLD", "SOLD", "SALE", "CREDIT"}

    if normalised in buys:
        return Side.BUY
    if normalised in sells:
        return Side.SELL
    raise ValueError(f"unrecognised side {raw!r}")


def normalise_symbol(raw: str) -> str:
    """Upper-case and strip a ticker.

    Deliberately does not strip exchange suffixes (``VOD.L``). Two brokers may
    disagree about whether ``VOD`` and ``VOD.L`` are the same instrument, and
    silently merging them would be a data-integrity bug that is very hard to
    spot downstream. Better to keep them distinct and let a later stage decide.
    """
    return raw.strip().upper()
