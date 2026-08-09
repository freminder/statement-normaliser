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

**Decision:** Timeline (T+1): Most standard stock and ETF trades settle on a `T+1 basis` (Trade date plus one business day). If you buy on Monday, it settles on Tuesday.
**Rejected:**
**Why:**
**Revisit if:**

## 5. Where the TOTAL-row filter lives

**Decision:** io.py filter
**Rejected:**
**Why:**
**Revisit if:**

## 6. Ticker identity across sources

**Decision:**  `VOD` trades on the U.S. NASDAQ exchange, whereas `VOD.L` trades on the London Stock Exchange (LSE). `Currency`: `VOD` is priced and settled in U.S. Dollars `(USD)`, while `VOD.L` is priced and quoted in British pence `(GBX/GBp)` or pounds. VOD and VOD.L stay distinct; instrument identity includes the exchange.
**Rejected:**
**Why:**
**Revisit if:** GBP assumed, GBX would need detection and a 100× correction.

## 7. Fee across sources
**Decision:** Because Broker D does not declare Fee, I will take 1.5 USD, same as Broker A.
**Rejected:** When data quality becomes of high standards or broker report the true Fee. Platform commission be declared.
**Why:** I assume that both Brokers have the same platform, therefore same commission.
**Revisit if:** When data quality becomes of high standards or broker report the true Fee. Platform commission be declared.

## 8. Quantity Symbol declares Side across sources
**Decision:** Broker C does not report Side clearly, but as part of the Quantity. `Negative` Quantity means `SELL`, `Positive` Quantity means `BUY`.
**Rejected:** When an official declaration comes.
**Why:**
**Revisit if:** after new information comes

### 7. Added ci.yml

### 8. Added rulesets in order to protect remote main from being deleted
