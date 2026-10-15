"""Regression tests with fictional Fidelity positions (no account data)."""

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from main import read_fidelity_csv, summarize


HEADER = "Account number,Symbol,Description,Quantity,Last price,Current value"
ROWS = [
    "EXAMPLE,SPAXX**,HELD IN MONEY MARKET,,,$200.00",
    "EXAMPLE, -ACME261218C100,ACME DEC 18 2026 $100 CALL,2,$3.00,$600.00",
    "EXAMPLE, -ACME261218P90,ACME DEC 18 2026 $90 PUT,-1,$4.00,-$400.00",
    "EXAMPLE,ACME,ACME CORPORATION,3,$50.00,$150.00",
    "EXAMPLE,Pending activity,Pending activity,,,$-20.00",
]


class PortfolioTests(unittest.TestCase):
    def load(self, with_quotes=False):
        header = HEADER + (",Bid,Ask" if with_quotes else "")
        rows = [
            row + (",," if index in (0, 3, 4) else (",$2.00,$4.00" if index == 1 else ",$3.00,$5.00"))
            if with_quotes else row
            for index, row in enumerate(ROWS)
        ]
        # Include Fidelity's extra blank trailing cell and footer.
        content = header + "\n" + "\n".join(row + "," for row in rows) + "\n" + (
            '"The data and information provided are subject to change."\n'
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "positions.csv"
            path.write_text(content, encoding="utf-8-sig")
            return summarize(read_fidelity_csv(path))

    def test_missing_bid_ask_uses_last_and_no_double_count(self):
        df, amounts, total, fidelity, mids, fallbacks, missing = self.load()
        self.assertEqual((mids, fallbacks, missing), (0, 2, 0))
        self.assertAlmostEqual(amounts["Options"], 200)
        self.assertAlmostEqual(amounts["SPAXX"], 200)
        self.assertAlmostEqual(amounts["Pending Activity"], -20)
        self.assertAlmostEqual(amounts["Other securities"], 150)
        self.assertAlmostEqual(total, 530)
        self.assertAlmostEqual(fidelity, 530)
        self.assertEqual(df.loc[df["Asset Type"] == "Option", "Price Source"].tolist(), ["Last", "Last"])

    def test_unpriced_long_option_remains_missing(self):
        from io import StringIO
        import pandas as pd

        sample = pd.read_csv(StringIO(HEADER + "\n" + "\n".join(ROWS + [
            "EXAMPLE, -ACME270115C150,ACME JAN 15 2027 $150 CALL,1,--,--"
        ])))
        df, amounts, total, fidelity, mids, fallbacks, missing = summarize(sample)
        self.assertEqual((mids, fallbacks, missing), (0, 2, 1))
        self.assertEqual(df.iloc[-1]["Price Source"], "Unavailable")
        self.assertTrue(pd.isna(df.iloc[-1]["Calculated Value"]))
        self.assertAlmostEqual(total, 530)

    def test_midpoints_override_last_only_for_options(self):
        df, amounts, total, fidelity, mids, fallbacks, missing = self.load(with_quotes=True)
        self.assertEqual((mids, fallbacks, missing), (2, 0, 0))
        self.assertAlmostEqual(amounts["Options"], 200)
        self.assertAlmostEqual(total, 530)
        self.assertAlmostEqual(fidelity, 530)
        self.assertEqual(df.loc[df["Asset Type"] == "Option", "Price Source"].tolist(), ["Midpoint", "Midpoint"])


if __name__ == "__main__":
    unittest.main()
