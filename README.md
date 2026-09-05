# Statement Normaliser

Turns broker statement CSVs from four different sources into one canonical schema.

## The problem

Four brokers, four CSV formats. Different column names, four date formats, four
side conventions, two currencies — and every source awkward in a different way:

| Source | The awkward bit |
|---|---|
| **A** | The easy case. ISO dates, explicit columns. |
| **B** | `DD/MM/YYYY` dates, `B`/`S` labels, `£` prefixes, quantities quoted as `"1,000"`, no fee column |
| **C** | No side column at all — direction is encoded in the *sign* of the quantity. Reports settlement date, not trade date. |
| **D** | No price column — only a gross amount, with fees bundled in. A `TOTAL` summary row at the bottom that will corrupt every downstream number if it isn't caught. |

This isn't a contrived exercise. Reconciling client data that arrives in formats
nobody documented is the first two weeks of most engagements.

## Results

```
$ uv run normalise --input examples/ --output out/canonical.csv
INFO statement_normaliser.io: parsing broker_a.csv with broker_a
INFO statement_normaliser.io: parsing broker_b.csv with broker_b
INFO statement_normaliser.io: parsing broker_c.csv with broker_c
INFO statement_normaliser.io: parsing broker_d.csv with broker_d
INFO statement_normaliser.io: wrote 13 transactions to out/canonical.csv
```

```
trade_date,symbol,side,quantity,price,fees,currency,source
2024-01-15,AAPL,BUY,100,150.00,1.50,USD,broker_a
2024-01-15,AMZN,BUY,10,155.24,0,USD,broker_d
2024-01-15,VOD.L,BUY,1000,0.69,0,GBP,broker_b
2024-01-16,AAPL,BUY,200,149.10,2.95,USD,broker_c
2024-02-20,AAPL,SELL,75,168.40,2.95,USD,broker_c
2024-02-20,MSFT,BUY,50,410.25,1.50,USD,broker_a
2024-03-08,AMZN,BUY,5,177.23,0,USD,broker_d
2024-03-11,AAPL,SELL,40,172.80,1.50,USD,broker_a
2024-04-03,BP.L,BUY,500,4.82,0,GBP,broker_b
2024-04-08,TSLA,BUY,50,171.05,2.95,USD,broker_c
2024-05-02,NVDA,BUY,25,880.10,1.50,USD,broker_a
2024-06-22,VOD.L,SELL,400,0.74,0,GBP,broker_b
2024-06-27,AMZN,SELL,8,193.50,0,USD,broker_d
```

| | |
|---|---|
| Sources parsed | 4 formats → 1 schema |
| Rows in / out | 14 data rows → **13 transactions** (1 summary row skipped) |
| Per source | A: 4 · B: 3 · C: 3 · D: 3 |
| Currencies | GBP and USD, side by side, **unconverted** |
| Tests | **96 passing**, 1 skipped, 96% coverage, 0.6s |
| Runtime dependencies | **none** — standard library only |

**Reconciliation check.** Broker D reports no price, so it's derived as
gross ÷ units. Multiplied back out, the three parsed rows sum to **3986.55** —
exactly the `TOTAL` row the parser discards. The source proves the parser
correct, to the cent.

## Design decisions

Full reasoning in [DECISIONS.md](DECISIONS.md). The three that shaped everything:

**Normalise representation, never value.** Dates, tickers, column names and side
labels are *representation* — normalise them freely. Prices, quantities and
currencies are *facts about what happened* — preserve them exactly. So GBP and
USD rows sit in the same file, each unambiguous because `currency` says which.
Nothing is FX-converted at ingestion: that needs a rate, and a rate needs a date
and a source, and baking one in silently destroys the ability to reproduce what
the broker actually reported.

**Direction lives in `side`, never in a sign.** Broker C encodes sells as
negative quantities. The canonical model keeps quantity positive and forces that
translation into the parser, where it's visible and tested, rather than leaking a
second representation through the codebase.

**Instrument identity includes the exchange.** `VOD` (NASDAQ, USD) and `VOD.L`
(LSE, GBP) are different instruments with different ADR ratios. Merging them
would corrupt share counts by an integer factor, silently and permanently.

## Architecture

```
src/statement_normaliser/
├── models.py     # Transaction — frozen, self-validating, Decimal money
├── errors.py     # exception hierarchy; every message names file + line
├── core.py       # pure parsing logic — no file or network I/O
├── parsers.py    # one class per broker + dispatch registry
├── io.py         # the only module allowed to touch disk
└── cli.py        # thin entry point, zero business logic
```

The rule that matters: **`core.py` never opens a file.** It logs, but it reads
and writes nothing; all real I/O lives at the edges. That's why `test_core.py` needs no fixtures, no temp directories and no
mocking, and why the whole suite runs in a tenth of a second.

Adding a fifth broker means one class and one registry entry. Nothing that
already works is touched.

## Quickstart

```bash
uv sync
uv run pytest --cov=src
uv run normalise --input examples/ --output out/canonical.csv
```

Install it as a standalone tool, no Python knowledge required at the far end:

```bash
uv tool install .
normalise --input ~/statements --output canonical.csv
```

```
usage: normalise [-h] --input INPUT --output OUTPUT [--lenient] [--dry-run] [-v]

  --input     directory containing broker statement CSVs
  --output    path to write the canonical CSV
  --lenient   log and skip unparsable rows instead of failing (default: fail)
  --dry-run   parse and report, but write nothing
```

Strict is the default deliberately. Skip-and-log by default means a broken export
silently drops 400 of 1,000 rows and you reconcile to a confidently wrong number.
Loud failure costs minutes; quiet data loss costs a client's trust.

## Where this fails

**Broker C's dates are derived, not reported.** The source gives a settlement
date; the trade date is computed as one *business* day earlier, stepping over
weekends. That is right for US equities from 28 May 2024 onward. It is wrong
before that date, and wrong for UK and EU rows, which stay on T+2 until
11 October 2027 — the Broker C rows in `examples/` fall in that earlier window
and are off by one business day. Exchange holidays are not handled either:
Good Friday and Easter Monday count as trading days. **The correct fix is to
obtain trade dates from the source rather than derive them.** This is the
largest known defect and it is deliberately visible rather than hidden. See
`DECISIONS.md` 4.

**Broker D's fees are unknown, recorded as zero.** They're bundled into the gross
amount. So the derived price is fee-inflated: it reconciles against the source's
own total, but it is not a clean execution price. `fees = 0` means *not
separately reported*, not *none charged* — the schema has no way to say
"unknown".

**No FX.** GBP and USD rows coexist and are not comparable without a rate. Any
total across currencies is meaningless. That's correct for an ingestion layer and
a problem for whatever consumes it.

**No corporate actions.** A stock split makes historical quantities wrong. No
detection, no adjustment.

**Whole file held in memory.** Fine at 10⁵ rows, not at 10⁸.

**UTF-8 assumed.** A Latin-1 export raises on read rather than mangling silently,
which is the right direction, but it isn't handled.

**`%b` is locale-dependent.** `strptime` matches month abbreviations for the
machine's locale. Parsing `17-Jan-2024` works on an English system and may not on
another. Untested against a non-English locale.

## What I'd do with another week

1. Give Broker C's date arithmetic an exchange holiday calendar — weekends are
   handled, holidays are not — or better, go back to the source for real trade
   dates
2. Property-based tests with `hypothesis` for the money and date parsers
3. Stream rows instead of materialising the whole file
4. A `--report` flag emitting per-source row counts, skip counts and
   reconciliation results, so a run is auditable without reading the logs
