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


def parse_money(series):
    return pd.to_numeric(
        series.astype(str)
            .replace("--", pd.NA)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False),
        errors="coerce",
    )

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

    required = {
        "Last Price": last_price_col,
        "Bid": bid_col,
        "Ask": ask_col,
        "Quantity": qty_col,
        "Current Value": market_value_col,
        "Symbol": symbol_col,
    }

    missing = [name for name, col in required.items() if col is None]

    if missing:
        print("Missing required columns:")
        for name in missing:
            print(f"  - {name}")
        return 1

    last = parse_money(df[last_price_col])
    bid = parse_money(df[bid_col])
    ask = parse_money(df[ask_col])

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

    current_value = parse_money(df[market_value_col]).fillna(0)

    df["Asset Type"] = "Option"

    df.loc[
        df[symbol_col].str.startswith("SPAXX", na=False),
        "Asset Type",
    ] = "Cash"

    df.loc[
        df[symbol_col].str.contains(
            "Pending Activity",
            case=False,
            na=False,
        ),
        "Asset Type",
    ] = "Pending"


    midpoint_total = df["Mid Value"].sum(skipna=True)
    spaxx_total = current_value[df["Asset Type"] == "Cash"].sum()
    pending_total = current_value[df["Asset Type"] == "Pending"].sum()

    total_portfolio = midpoint_total + spaxx_total + pending_total

    fidelity_total = None
    difference = None

    if market_value_col:
        fidelity_total = (
            current_value
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
