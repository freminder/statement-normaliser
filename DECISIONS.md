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

**Decision:** _(yours — Broker C gives you settlement date)_
**Rejected:**
**Why:**
**Revisit if:**

## 5. Where the TOTAL-row filter lives

**Decision:** _(yours — parser hook or io.py filter?)_
**Rejected:**
**Why:**
**Revisit if:**

## 6. Ticker identity across sources

**Decision:** _(yours — is `VOD` the same instrument as `VOD.L`?)_
**Rejected:**
**Why:**
**Revisit if:**
