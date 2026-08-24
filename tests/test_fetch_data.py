import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fetch_data  # noqa: E402


class EtfFundFlowTests(unittest.TestCase):
    def test_parses_state_street_page(self):
        text = (
            "Fund Net Asset Value | as of Aug 21 2026 | NAV | definition | "
            "$765.58 | Shares Outstanding | 1,071.33 M | Assets Under Management | $820,189.93 M"
        )
        row = fetch_data.parse_etf_fund_page(text, "ssga")
        self.assertEqual(row["as_of"], "2026-08-21")
        self.assertEqual(row["nav"], 765.58)
        self.assertEqual(row["shares_outstanding"], 1_071_330_000)

    def test_parses_ishares_page(self):
        text = (
            'NAV as of","value":"81.98","valueReference":{"value":"Aug 21, 2026"} | '
            "Shares Outstanding | 564,100,000 | as of | Aug 21, 2026"
        )
        row = fetch_data.parse_etf_fund_page(text, "ishares")
        self.assertEqual(row["as_of"], "2026-08-21")
        self.assertEqual(row["shares_outstanding"], 564_100_000)

    def test_calculates_cross_day_creation_redemption_proxy(self):
        ssga = (
            "Fund Net Asset Value | as of Aug 21 2026 | NAV | definition | "
            "$10.00 | Shares Outstanding | 101.00 M | Assets Under Management | $1,010.00 M"
        )
        ishares = (
            'NAV as of","value":"10.00","valueReference":{"value":"Aug 21, 2026"} | '
            "Shares Outstanding | 101,000,000 | as of | Aug 21, 2026"
        )
        globalx = (
            "Key Information | As of | Aug 21 2026 | Net Assets | $1.01 billion | NAV | $ | 10.00 | "
            "Trading Details | As of | Aug 21 2026 | Shares Outstanding | 101,000,000"
        )
        previous = [
            {"symbol": source["symbol"], "as_of": "2026-08-20", "nav": 10, "shares_outstanding": 100_000_000, "history": []}
            for source in fetch_data.ETF_FUND_SOURCES
        ]

        def page(url, timeout=45):
            if "ishares" in url:
                return ishares
            if "globalx" in url:
                return globalx
            return ssga

        with patch.object(fetch_data, "get_page_text", side_effect=page), patch.object(fetch_data.time, "sleep"):
            rows = fetch_data.fetch_etf_fund_flows(previous)

        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["shares_change"] == 1_000_000 for row in rows))
        self.assertTrue(all(row["estimated_flow"] == 10_000_000 for row in rows))


if __name__ == "__main__":
    unittest.main()
