# Portfolio Tracker v0.1

## Setup

Requires Python 3.12 or newer.

From the repository root, create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Place your Fidelity export in `data/Portfolio_Positions.xlsx`, then run:

```bash
python src/main.py
```

For subsequent terminal sessions, activate the environment with `source .venv/bin/activate` before running the application. This keeps project packages separate from a system or Homebrew-managed Python installation.

## Output

Version 0.1 reads the Fidelity export, computes `Mid = (Bid + Ask) / 2` when Bid/Ask columns exist, and writes `output/OpenPositions_Midpoint.xlsx`.
