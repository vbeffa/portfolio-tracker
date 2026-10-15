# Portfolio Tracker v0.1

Calculate midpoint values for a Fidelity options portfolio from a Fidelity CSV positions export.

## Requirements

- Python 3.12 or newer

## Setup

From the repository root, create and activate a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

This avoids installing packages into a system or Homebrew-managed Python environment. In a new terminal session, run `source .venv/bin/activate` again before using the application.

## Usage

Export your positions from Fidelity as a CSV file, then run:

```bash
python src/main.py /path/to/Portfolio_Positions.csv
```

The input CSV path is required. The script expects columns for Symbol, Last Price, Bid, Ask, Quantity (or Qty), and Current Value. If required columns are missing, it reports them and exits.

## Output

The script prints a portfolio summary including option midpoint valuation, SPAXX cash, pending activity, total portfolio value, Fidelity market value, and the difference. Midpoint price is calculated as `(Bid + Ask) / 2`, falling back to Last Price where bid/ask values are unavailable.

Version 0.1 does not yet write an XLSX output file.
