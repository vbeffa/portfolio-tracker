#!/usr/bin/env python3
"""Summarize a Fidelity positions CSV, using option midpoints when available."""

import argparse
from io import StringIO
from pathlib import Path

import pandas as pd


COLUMN_MAP = {
    "last_price": ["Last price"],
    "bid": ["Bid"],
    "ask": ["Ask"],
    "quantity": ["Quantity", "Qty"],
    "market_value": ["Current value"],
    "symbol": ["Symbol"],
    "description": ["Description"],
}


def get_column(columns, logical_name):
    lookup = {name.lower().strip(): name for name in columns}
    return next(
        (lookup[name.lower()] for name in COLUMN_MAP[logical_name] if name.lower() in lookup),
        None,
    )


def parse_money(series):
    return pd.to_numeric(
        series.astype("string")
        .str.strip()
        .replace({"--": pd.NA, "": pd.NA})
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("+", "", regex=False),
        errors="coerce",
    )


def read_fidelity_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        lines = file.readlines()

    # Fidelity may append a disclaimer after the positions.
    for index, line in enumerate(lines):
        if line.startswith('"The data and information'):
            lines = lines[:index]
            break

    if not lines:
        raise ValueError("The CSV is empty.")

    # Fidelity exports sometimes have one extra empty cell per data row.
    if len(lines) > 1 and lines[0].count(",") < lines[1].count(","):
        lines[0] = lines[0].rstrip("\r\n") + ",\n"

    df = pd.read_csv(StringIO("".join(lines)), dtype={"Symbol": "string"})
    df = df.loc[:, ~df.columns.str.startswith("Unnamed:")].copy()
    return df.dropna(how="all")


def summarize(df):
    symbol_col = get_column(df.columns, "symbol")
    value_col = get_column(df.columns, "market_value")
    quantity_col = get_column(df.columns, "quantity")
    last_col = get_column(df.columns, "last_price")
    bid_col = get_column(df.columns, "bid")
    ask_col = get_column(df.columns, "ask")
    desc_col = get_column(df.columns, "description")

    required = {
        "Symbol": symbol_col,
        "Current Value": value_col,
        "Quantity": quantity_col,
        "Last Price": last_col,
    }
    missing = [name for name, column in required.items() if column is None]
    if missing:
        raise ValueError("Missing required columns:\n" + "\n".join(f"  - {name}" for name in missing))

    symbols = df[symbol_col].astype("string").fillna("").str.strip()
    descriptions = (
        df[desc_col].astype("string").fillna("")
        if desc_col else pd.Series("", index=df.index, dtype="string")
    )
    quantity = pd.to_numeric(df[quantity_col], errors="coerce")
    current = parse_money(df[value_col])
    last = parse_money(df[last_col])

    cash = symbols.str.match(r"^SPAXX(?:\*+)?$", case=False, na=False)
    pending = symbols.str.contains("Pending activity", case=False, na=False)
    # Fidelity formats options as e.g. " -AAOI261218C260".
    options = (
        symbols.str.match(r"^-?[A-Z]+\d{6}[CP]\d+(?:\.\d+)?$", case=False, na=False)
        | descriptions.str.contains(r"\b(?:CALL|PUT)\b", case=False, regex=True, na=False)
    ) & ~cash & ~pending
    other = ~(cash | pending | options)

    if bid_col is not None and ask_col is not None:
        bid = parse_money(df[bid_col])
        ask = parse_money(df[ask_col])
        has_midpoint = options & bid.notna() & ask.notna()
        midpoint = (bid + ask) / 2
    else:
        has_midpoint = pd.Series(False, index=df.index)
        midpoint = pd.Series(float("nan"), index=df.index)

    price = midpoint.where(has_midpoint, last)
    option_value = (price * quantity * 100).where(options)
    # If no usable quote exists, Fidelity's own current value is still usable.
    option_value = option_value.fillna(current.where(options))

    df = df.copy()
    df["Asset Type"] = "Other"
    df.loc[options, "Asset Type"] = "Option"
    df.loc[cash, "Asset Type"] = "Cash"
    df.loc[pending, "Asset Type"] = "Pending"
    df["Price Source"] = ""
    df.loc[options & has_midpoint, "Price Source"] = "Midpoint"
    df.loc[options & ~has_midpoint & last.notna(), "Price Source"] = "Last"
    df.loc[options & ~has_midpoint & last.isna() & current.notna(), "Price Source"] = "Fidelity value"
    df["Calculated Value"] = current
    df.loc[options, "Calculated Value"] = option_value[options]

    # Every position contributes to exactly one category.
    amounts = {
        "Options": df.loc[options, "Calculated Value"].sum(),
        "Other securities": current[other].sum(),
        "SPAXX": current[cash].sum(),
        "Pending Activity": current[pending].sum(),
    }
    total = sum(amounts.values())
    fidelity_total = current.sum()
    return df, amounts, total, fidelity_total, int((options & has_midpoint).sum()), int((options & ~has_midpoint).sum())


def main():
    parser = argparse.ArgumentParser(description="Summarize Fidelity positions and available option midpoints.")
    parser.add_argument("input_csv", type=Path, help="Fidelity positions CSV")
    args = parser.parse_args()

    if not args.input_csv.is_file():
        parser.error(f"File not found: {args.input_csv}")

    try:
        df, amounts, total, fidelity_total, mids, fallbacks = summarize(read_fidelity_csv(args.input_csv))
    except (ValueError, pd.errors.ParserError) as error:
        print(error)
        return 1

    difference = total - fidelity_total
    percentage = difference / fidelity_total * 100 if fidelity_total else 0
    print("\nPortfolio Summary")
    print("-----------------")
    print(f"Positions:                {len(df):>15}")
    print(f"Options (mixed quotes):  ${amounts['Options']:>15,.2f}")
    print(f"  Midpoint quotes:        {mids:>15}")
    print(f"  Fallback quotes:        {fallbacks:>15}")
    print(f"Other securities:        ${amounts['Other securities']:>15,.2f}")
    print(f"SPAXX:                   ${amounts['SPAXX']:>15,.2f}")
    print(f"Pending Activity:        ${amounts['Pending Activity']:>15,.2f}")
    print(f"Total Portfolio Value:   ${total:>15,.2f}")
    print(f"Fidelity Market Value:   ${fidelity_total:>15,.2f}")
    print(f"Difference:              ${difference:>15,.2f} ({percentage:+.2f}%)")
    if fallbacks:
        print("Note: Options without bid/ask use Last price, or Fidelity value if Last is missing.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
