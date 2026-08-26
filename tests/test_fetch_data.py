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


class DerivedAnalyticsTests(unittest.TestCase):
    def test_ai_chain_uses_quote_inputs(self):
        quotes = []
        for symbol in ("NVDA", "AMD", "MU", "AVGO"):
            quotes.append({"symbol": symbol, "change_pct": 2, "volume": 120, "avg_volume": 100, "price": 10, "pe": 30})
        rows = fetch_data.build_ai_chain_metrics(quotes)
        self.assertEqual(rows[0]["group"], "GPU / HBM")
        self.assertEqual(rows[0]["breadth"], 100)
        self.assertGreater(rows[0]["strength"], 70)

    def test_backtest_is_generated_without_future_signal_inputs(self):
        points = [{"date": f"2026-01-{(i % 28) + 1:02d}", "close": 100 + i * 0.4 + (i % 5) * 0.1} for i in range(126)]
        history = [{"symbol": symbol, "points": points} for symbol in ("SPY", "TLT", "CPER", "GLD", "UUP", "BOTZ", "EWH", "ASHR")]
        rows = fetch_data.build_score_backtest(history)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["history_days"] == 126 for row in rows))
        self.assertTrue(all(0 <= row["current_percentile"] <= 100 for row in rows))

    def test_event_calendar_filters_official_releases(self):
        payload = {"release_dates": [
            {"release_name": "Consumer Price Index", "date": "2026-09-11"},
            {"release_name": "Unrelated Weekly Series", "date": "2026-09-12"},
        ]}
        with patch.object(fetch_data, "local_key", return_value="x" * 32), patch.object(fetch_data, "get_json", return_value=payload), patch.object(fetch_data, "get_page_text", side_effect=ValueError("offline")):
            rows = fetch_data.fetch_event_calendar()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "美国CPI")
        self.assertEqual(rows[0]["source_name"], "FRED官方发布日历")


if __name__ == "__main__":
    unittest.main()
