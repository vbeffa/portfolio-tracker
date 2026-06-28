#!/usr/bin/env python3

from pathlib import Path
import argparse

import pandas as pd
from io import StringIO


COLUMN_MAP = {
    "last_price": ["Last price"],
    "bid": ["Bid"],
    "ask": ["Ask"],
    "quantity": ["Quantity", "Qty"],
    "market_value": ["Current value"],
    "symbol": ["Symbol"],
}


def build_lookup(columns) -> dict[str, str]:
    return {column.lower().strip(): column for column in columns}


def get_column(lookup: dict[str, str], logical_name: str) -> str | None:
    for candidate in COLUMN_MAP.get(logical_name, []):
        column = lookup.get(candidate.lower())
        if column:
            return column
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Calculate midpoint values for a Fidelity options portfolio."
    )

    parser.add_argument(
        "input_csv",
        type=Path,
        help="Input Fidelity CSV file",
    )

    return parser.parse_args()


def format_currency(ws, headers, column_name):
    if column_name and column_name in headers:
        col = headers[column_name]
        for row in range(2, ws.max_row + 1):
            ws.cell(row, col).number_format = "$#,##0.00"


def main() -> int:
    args = parse_args()

    input_path = args.input_csv

    if not input_path.exists():
        print(f"Error: '{input_path}' does not exist.")
        return 1

    #
    # Read CSV
    #

    with open(input_path, encoding="utf-8-sig") as f:
        lines = f.readlines()

    # Fidelity's disclaimer marks the beginning of the footer.
    for i, line in enumerate(lines):
        if line.startswith('"The data and information'):
            lines = lines[:i]
            break

    # Fix Fidelity's missing trailing comma in the header.
    header = lines[0].rstrip("\n")
    if header.count(",") < lines[1].count(","):
        lines[0] = header + ",\n"

    df = pd.read_csv(StringIO("".join(lines)))

    # Remove the dummy column created by Fidelity's malformed header.
    df = df.loc[:, ~df.columns.str.startswith("Unnamed:")].copy()

    lookup = build_lookup(df.columns)

    last_price_col = get_column(lookup, "last_price")
    bid_col = get_column(lookup, "bid")
    ask_col = get_column(lookup, "ask")
    qty_col = get_column(lookup, "quantity")
    market_value_col = get_column(lookup, "market_value")
    symbol_col = get_column(lookup, "symbol")

    if bid_col is None:
        print("Error: Could not locate Bid column.")
        return 1

    if ask_col is None:
        print("Error: Could not locate Ask column.")
        return 1

    last = pd.to_numeric(
        df[last_price_col]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    )
    bid = pd.to_numeric(df[bid_col].replace("--", pd.NA), errors="coerce")
    ask = pd.to_numeric(df[ask_col].replace("--", pd.NA), errors="coerce")

    if qty_col:
        quantity = pd.to_numeric(df[qty_col], errors="coerce").fillna(1)
    else:
        quantity = 1

    #
    # Calculations
    #

    mid = (bid + ask) / 2

    # If bid/ask are unavailable, fall back to the last traded price.
    mid = mid.fillna(last)

    df["Mid"] = mid
    df["Mid Value"] = mid * quantity * 100

    current_value = pd.to_numeric(
        df[market_value_col]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0)

    spaxx_mask = (
        df[symbol_col]
        .fillna("")
        .astype(str)
        .str.startswith("SPAXX")
    )

    pending_mask = (
        df[symbol_col]
        .fillna("")
        .astype(str)
        .str.contains("Pending Activity", case=False, regex=False)
    )


    midpoint_total = df["Mid Value"].sum(skipna=True)
    spaxx_total = current_value.loc[spaxx_mask].sum()
    pending_total = current_value.loc[pending_mask].sum()

    total_portfolio = midpoint_total + spaxx_total + pending_total

    fidelity_total = None
    difference = None

    if market_value_col:
        fidelity_total = (
            pd.to_numeric(
                df[market_value_col]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False),
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        difference = midpoint_total - fidelity_total

    #
    # Summary
    #

    print()
    print("Portfolio Summary")
    print("-----------------")
    print(f"Positions:                {len(df):>15}")
    print()
    print(f"Options (Midpoint):      ${midpoint_total:>15,.2f}")
    print(f"SPAXX:                   ${spaxx_total:>15,.2f}")
    print(f"Pending Activity:        ${pending_total:>15,.2f}")
    print("                         ----------------")
    print(f"Total Portfolio Value:   ${total_portfolio:>15,.2f}")


    if fidelity_total is not None:
        difference = total_portfolio - fidelity_total
        percent = difference / fidelity_total * 100 if fidelity_total else 0
        sign = "+" if difference >= 0 else ""
        print()
        print(f"Fidelity Market Value:   ${fidelity_total:>15,.2f}")
        print(f"Difference:              ${difference:>15,.2f} ({sign}{percent:.2f}%)")

    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
