# Portfolio Tracker

A Python command-line tool that summarizes a Fidelity positions CSV. Options use the
bid/ask midpoint when both quotes are present. Fidelity's normal CSV export omits
these columns, so options fall back to **Last price** (or Fidelity's current value
if Last is missing). A last price is **not** a midpoint.

Cash (SPAXX), pending activity, and non-option securities use Fidelity's reported
current value rather than the options contract multiplier. The summary compares
the resulting portfolio valuation with Fidelity's reported total. Options with
wide bid/ask spreads can differ substantially from their last-traded prices.

## Setup

Requires Python 3.12 or newer. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

Download a **CSV** of positions from Fidelity, then run:

```bash
python src/main.py ~/Downloads/Portfolio_Positions.csv
```

The script prints a summary to the terminal; it does not create an Excel file.
It reports how many option positions had midpoint quotes and how many required
fallback prices. No account login or external quote retrieval is performed.

## Tests

```bash
python -m unittest discover -s tests -v
```

Keep real brokerage exports out of Git; the tests use invented account data.

## Missing quotes

If an option has neither usable bid/ask, Last price, nor Current value,
its calculated value remains missing. The report labels the sum as a **partial
valuation total**, counts the missing positions, and prints their symbols.
The Fidelity Market Value comparison is also incomplete for these rows.
The program does not assume that an unquoted option is worthless.
