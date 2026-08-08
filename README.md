# Statement Normaliser

Turns broker statement CSVs from four different sources into one canonical schema.

> **This repo is a scaffold, not a finished project.** Broker A is implemented as
> a worked reference. Brokers B, C and D are yours. The point is to have a
> concrete example of the standard before you write your own code — not to have
> the work done for you. Delete this box when you finish.

## The problem

Four brokers, four CSV formats. Different column names, four date formats, one
source signs sells as negative quantities instead of labelling them, one bundles
fees into the price, one appends a `TOTAL` row at the bottom that will quietly
corrupt every downstream number if you don't catch it.

This is not a contrived exercise. Reconciling client data that arrives in
formats nobody documented is the first two weeks of most engagements.

## What's built

```
src/statement_normaliser/
├── models.py     # Transaction — immutable, self-validating, Decimal money
├── errors.py     # exception hierarchy; every message names file + line
├── core.py       # PURE parsing logic — no I/O, testable with literals
├── parsers.py    # one class per broker + dispatch registry  ← YOUR WORK
├── io.py         # the only module allowed to touch disk
└── cli.py        # thin entry point, zero business logic
```

The structural rule worth internalising: `core.py` never opens a file. All I/O
lives at the edges. That is why `test_core.py` needs no fixtures, no temp
directories and no mocking — and why the tests run in milliseconds.

## Quickstart

```bash
uv sync
uv run pytest --cov=src        # 40 tests passing, 98% coverage
uv run ruff check . && uv run mypy    # both clean
```

Then run it. On the full `examples/` folder it will **fail on purpose**:

```
$ uv run normalise --input examples/ --output out.csv
INFO  parsing broker_a.csv with broker_a
ERROR no parser matched headers ['Date', 'Instrument', 'B/S', ...] in examples/broker_b.csv
```

That error is the assignment. Brokers B, C and D have no parsers yet.


## Your assignment

Implement three parsers in `parsers.py`. Each is awkward in a different, and
deliberately realistic, way:

| Broker | The awkward bit | What you'll have to decide |
|---|---|---|
| **B** | `DD/MM/YYYY` dates, `B`/`S`, £ symbols, quoted thousands, no fee column | Is `03/04/2024` March or April? Your `date_formats` is the answer — justify it in `DECISIONS.md`. |
| **C** | Negative quantity = sell, no action column, *settlement* date | Where does sign→side translation belong, and what does the settlement/trade date mismatch do to your P&L? |
| **D** | A `TOTAL` summary row; fees baked into a gross amount | A parser only sees one row at a time. Add a `should_skip()` hook to the base class, or filter in `io.py`? Both work. Pick one and defend it. |

For each: write the tests **first**, then the parser. Then run the checklist.

## Done when

- [ ] All four brokers parse
- [ ] `uv run pytest --cov=src` passes, ≥80% coverage
- [ ] `uv run ruff check . && uv run mypy src/` clean
- [ ] `DECISIONS.md` has your three decisions, with rejected alternatives
- [ ] A **Results** section below with real numbers
- [ ] A **Where this fails** section below, written honestly
- [ ] Explain-back test passed: close the editor, explain every choice out loud

## Results

<!-- Fill this in. Numbers, not adjectives. Example shape: -->
<!-- | Source | Rows in | Parsed | Skipped | Notes | -->
<!-- Then: total runtime on N rows. -->

## Where this fails

<!-- Fill this in honestly. Some real ones to get you started — verify each: -->
<!-- - Assumes UTF-8; a Latin-1 export will raise on read. -->
<!-- - No FX handling: GBP and USD rows sit in the same file, uncombined. -->
<!-- - No corporate actions. A stock split makes historical quantities wrong. -->
<!-- - Whole file loaded into memory; fine at 10^5 rows, not at 10^8. -->

## Design decisions

See [DECISIONS.md](DECISIONS.md).
