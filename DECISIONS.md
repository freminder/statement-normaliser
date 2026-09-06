# Decisions

Three lines per real decision: what you chose, what you rejected, why. Entries
1–3 are worked examples for the scaffold. Add yours as you go — minimum three
more by the time the project is done.

Format: **Decision / Rejected / Why / Revisit if.**

---

## 1. Decimal for all monetary values (scaffold)

**Decision:** `Decimal`, constructed from strings, for price, fees and quantity.
**Rejected:** `float`, which is faster and needs no imports.
**Why:** Binary floats cannot represent 0.10 exactly. Accumulated over a few
thousand rows the drift produces a reconciliation break, which in a regulated
firm is an incident and not a rounding error. `tests/test_core.py::
test_money_parsing_is_exact_not_approximate` is the demonstration.
**Revisit if:** never, for money. Use floats for statistics, not for cash.

## 2. Date formats declared per parser, not guessed globally (scaffold)

**Decision:** Each `StatementParser` subclass declares its own `date_formats`.
**Rejected:** One global "try everything" resolver.
**Why:** `03/04/2024` is 3 April under `%d/%m/%Y` and 3 March under `%m/%d/%Y`,
and both parse successfully. A global resolver would silently pick whichever
came first in the list and be wrong for one broker with no error raised. Silent
wrongness is the worst failure mode available. Declaring the format per source
turns an invisible bug into an explicit, reviewable statement of fact.
**Revisit if:** a source genuinely mixes formats within one file — then the
ambiguity has to be resolved from context, and that needs its own design.

## 3. Strict mode is the default (scaffold)

**Decision:** The first unparsable row aborts. `--lenient` opts out.
**Rejected:** Skip-and-log by default, which is friendlier on a first run.
**Why:** Skipping by default means a broken export silently drops 400 of 1,000
rows and you reconcile to a confidently wrong number. Loud failure costs
minutes; quiet data loss costs a client's trust.
**Revisit if:** this runs unattended on a schedule, where aborting the whole
batch for one bad row is worse — then lenient plus alerting on the skip rate.

---

## 4. Trade date vs settlement date

**Decision:** Timeline (T+1): Most standard stock and ETF trades settle on a `T+1 basis` (Trade date plus one business day = settlement day). If you buy on Monday, it settles on Tuesday.
**Rejected:** when occurred trade day is Saturday we use T+1 to setup a trade date. If occurred date after T+1 is a weekend then we use next working day, which should be Monday.
**Why:**
**Revisit if:**

## 5. Where the TOTAL-row filter lives

**Decision:** TOTAL filter lives in parsers class as `should_skip`.
**Rejected:**
**Why:**
**Revisit if:**

## 6. Ticker identity across sources

**Decision:**  `VOD` trades on the U.S. NASDAQ exchange, whereas `VOD.L` trades on the London Stock Exchange (LSE). `Currency`: `VOD` is priced and settled in U.S. Dollars `(USD)`, while `VOD.L` is priced and quoted in British pence `(GBX/GBp)` or pounds. VOD and VOD.L stay distinct; instrument identity includes the exchange.
**Rejected:**
**Why:**
**Revisit if:** GBP assumed, GBX would need detection and a 100× correction.

## 7. Fee across sources
**Decision:** Because Broker D does not declare Fee, I will take `0` USD, same as Broker A.
**Rejected:** When data quality becomes of high standards or broker report the true Fee. Platform commission be declared.
**Why:** I assume that both Brokers have the same platform, therefore same commission.
**Revisit if:** When data quality becomes of high standards or broker report the true Fee. Platform commission be declared.

## 8. Quantity Symbol declares Side across sources
**Decision:** Broker C does not report Side clearly, but as part of the Quantity. `Negative` Quantity means `SELL`, `Positive` Quantity means `BUY`.
**Rejected:** When an official declaration comes.
**Why:**
**Revisit if:** after new information comes

### 9. Added ci.yml

### 10. Added rulesets in order to protect remote main from being deleted

## 11. Derived unit prices are rounded to four decimal places

**Decision.** `core.derive_unit_price` divides gross by units and quantizes
the result to `Decimal("0.0001")` with `ROUND_HALF_UP`.

**Rejected.** Returning the raw quotient. `Decimal` division uses a 28
significant-digit context, so `100 / 3` yields
`33.33333333333333333333333333` — a price no statement ever printed, and a
column no human can read.

**Why.** Four decimal places is the equity convention. Broker D is the only
source that reports gross instead of price, so this is the only place a
derived number enters the pipeline.

**The cost, stated plainly.** After rounding, `quantity * price` no longer
reproduces the broker's gross amount exactly. For 10 units at $1,552.40 it
still does. For 3 units it does not. `Transaction.gross_value` is therefore
a *reconstruction*, not the statement's own figure.

**Revisit if.** A source reports FX or fixed income, where six to eight
decimal places are normal, or if a reconciliation step starts comparing
`gross_value` against the broker's own total.

## 12. A weekend trade date in source data warns, it does not reject

**Decision.** `core.warn_if_weekend` logs a WARNING naming the source, the
date and the day name, then returns the date unchanged. Brokers A, B and D
wrap their stated trade date in it.

**Rejected.** Raising `RowParseError`. Also rejected: silently accepting.

**Why.** `examples/broker_b.csv` reports a sale on Saturday 22 June 2024.
Markets were closed. The trade is still real money that moved — late
bookings, corrections and OTC trades all get stamped with odd dates.
Rejecting the row loses a position. Accepting it silently loses the signal.
A warning keeps both: the row lands in the output, and the operator can see
that it needs a phone call.

**Not applied to Broker C.** Its trade date comes from
`previous_business_day`, whose loop cannot return a weekend. A check there
would be dead code that looks like a safety net.

**Revisit if.** A reconciliation step starts failing on these rows, or a
holiday calendar arrives — a check that knows about weekends but not about
Good Friday is only half a check.

## 13. Optional columns use `.get` with a default, even when absent today

**Decision.** Fee and currency cells are read as `row.get("fee") or "0"` and
`row.get("ccy") or "USD"` in every parser, including Brokers B, C and D whose
files carry no such column.

**Rejected.** Hard-coding `Decimal("0")` and `"USD"` where the column provably
does not exist.

**Why.** Every `parse_row` reads the same shape, so a reader compares four
parsers without checking which columns each file happens to have. If a broker
starts sending a fee column, the parser picks it up with no code change. The
default is the documented behaviour from #7 — a missing fee is zero, not
unknown.

**The cost.** Four of these fallbacks never fire. `.get` implies the column is
sometimes present; here it never is. This entry is the only thing telling a
reader that.

**Required columns are still indexed.** `row["ccy"]` in Broker A and
`row["currency"]` in Broker B use brackets, because `required_headers`
guarantees them and `KeyError` is caught by `read_statement`. `.get` there
would return `None` and raise `AttributeError`, which is not caught.
