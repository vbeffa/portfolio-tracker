# Portfolio Tracker v0.1

1. Install Python 3.12+
2. pip install pandas openpyxl
3. Place your Fidelity export in data/Portfolio_Positions.xlsx
4. Run: python src/main.py

Version 0.1 reads the Fidelity export, computes Mid=(Bid+Ask)/2 when Bid/Ask columns exist,
and writes output/OpenPositions_Midpoint.xlsx.
