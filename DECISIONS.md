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

**Decision:** Broker C reports `SETTLE_DT`, not a trade date. Trade date is the
settlement date minus **one business day**, computed by
`core.previous_business_day`, which steps back one day and keeps stepping while
the result falls on a Saturday or Sunday.
**Rejected:** A fixed `settle - timedelta(days=2)`, which was what the code
originally did.
**Why:** T+1 is the settlement cycle for US and UK equities. Fixed calendar
arithmetic ignores weekends, and it produced `2024-04-07,TSLA,...,broker_c` in
`out/canonical.csv` — a Sunday, a day on which no trade can happen. The real
step is 1, 2 or 3 calendar days depending on where settlement lands: a Monday
settlement means a Friday trade. Hardcoding any single number is right at most
five days out of seven.
**Revisit if:** three known limits, all accepted for now.

1. *The cycle is not constant.* US equities only moved to T+1 on 28 May 2024;
   before that they were T+2, and UK and EU stay T+2 until 11 October 2027. The
   Broker C rows in `examples/` are dated January to April 2024, so under the
   rule in force at the time their true offset was two business days, not one.
   A date-dependent or per-broker offset is the correct fix; a single constant
   is not.
2. *No holiday calendar.* Good Friday 2024 (29 March) and Easter Monday
   (1 April) are treated as trading days. The standard library ships no
   exchange calendar and this project is standard library only.
3. *Deriving at all is second best.* A trade date obtained from the source
   beats any arithmetic. Ask the broker for the field before improving the
   formula.

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

## 9. Weekday arithmetic: standard library over hand-rolled

**Decision:** `date.weekday()`, with `SATURDAY = 5` named in `core.py`.
**Rejected:** Sakamoto's congruence — written by hand, tested, then deleted.
**Why:** Built first to understand what `weekday()` actually does, per the
curriculum rule of implementing a thing before using the library version. Same
answers on every date tried, in one line instead of a six-line month table with
a January/February year shift that is easy to get wrong. `weekday()` is C in
CPython and already tested upstream. Keeping both would have left two answers
to one question, in two different layers.
**Revisit if:** never, in CPython. Only relevant on a platform with no date
library at all.

## 10. A weekend settlement date warns, it does not fail

**Decision:** If `SETTLE_DT` itself falls on a weekend, log
`logger.warning` and keep parsing. The row still produces a transaction.
**Rejected:** Raising `RowParseError` and letting strict mode abort.
**Why:** A weekend settlement is suspicious data, not unparsable data — the
value is readable and the trade date derived from it is still a valid business
day. Decision #3 makes strict mode the default, so raising here would abort a
whole run over one odd date, which is the loud-failure rule applied where it
does not belong. The warning puts it in front of the operator without losing
the row. Note this puts `logging` inside `core.py`, which was otherwise a pure
module; accepted because logging performs no I/O of its own and the alternative
was duplicating the check in every parser.
**Revisit if:** weekend settlement dates turn out to signal a broken export
rather than a back-dated booking — then promote it to an error.

## 11. Added ci.yml

## 12. Added rulesets in order to protect remote main from being deleted
