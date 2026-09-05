import csv
import io
import json
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

        self.assertEqual(len(rows), len(fetch_data.ETF_FUND_SOURCES))
        self.assertTrue(all(row["shares_change"] == 1_000_000 for row in rows))
        self.assertTrue(all(row["estimated_flow"] == 10_000_000 for row in rows))
        self.assertTrue(all(row["asset_class"] in {"股票", "债券", "商品"} for row in rows))


class PublicMarketDataTests(unittest.TestCase):
    def test_parses_sina_continuous_futures_jsonp(self):
        text = '/*notice*/\nvar _RB0=([{"d":"2026-09-03","c":"3142.000","v":"802624"}]);'
        rows = fetch_data.parse_sina_futures_jsonp(text)
        self.assertEqual(rows[0]["d"], "2026-09-03")
        self.assertEqual(rows[0]["c"], "3142.000")

    def test_commodity_refresh_keeps_per_symbol_cache(self):
        previous = [{"symbol": spec[0], "name": spec[1], "price": 1} for spec in fetch_data.COMMODITY_SPECS]
        china_rows = [{"d": f"2026-08-{index + 1:02d}", "c": str(3100 + index), "v": "802624"} for index in range(21)]
        china = f"var _X=({json.dumps(china_rows)});"
        with patch.object(fetch_data, "get_json", side_effect=ValueError("limited")), patch.object(fetch_data, "get_text", return_value=china), patch.object(fetch_data.time, "sleep"):
            rows = fetch_data.fetch_commodity_market(previous)
        self.assertEqual(len(rows), len(fetch_data.COMMODITY_SPECS) + len(fetch_data.CHINA_COMMODITY_SPECS))
        self.assertEqual(sum(row.get("data_status") == "cached" for row in rows), len(fetch_data.COMMODITY_SPECS))

    def test_commodity_analytics_include_momentum_and_risk(self):
        points = [{"date": f"2026-01-{(index % 28) + 1:02d}", "close": 100 + index} for index in range(80)]
        metrics = fetch_data._changes_and_risk(points)
        self.assertGreater(metrics["change_20d"], 0)
        self.assertGreater(metrics["change_60d"], metrics["change_20d"])
        self.assertEqual(metrics["range_percentile"], 100)

    def test_parses_cftc_managed_money_positions(self):
        stream = io.StringIO()
        writer = csv.writer(stream)
        for prefix, _name in fetch_data.CFTC_MARKETS:
            fields = ["0"] * 80
            fields[0] = f"{prefix} - TEST EXCHANGE"
            fields[2] = "2026-08-25"
            fields[7] = "1000"
            fields[13] = "400"
            fields[14] = "250"
            fields[61] = "30"
            fields[62] = "10"
            writer.writerow(fields)
        with patch.object(fetch_data, "get_text", return_value=stream.getvalue()):
            result = fetch_data.fetch_cftc_positions()
        self.assertEqual(len(result), len(fetch_data.CFTC_MARKETS))
        self.assertEqual(result[0]["managed_money_net"], 150)
        self.assertEqual(result[0]["weekly_change"], 20)
        self.assertEqual(result[0]["net_pct_open_interest"], 15)

    def test_parses_tic_cross_border_totals(self):
        fields = ["0"] * 17
        fields[0], fields[1], fields[2] = "Grand Total", "99996", "2026-06"
        fields[4], fields[7], fields[10], fields[13], fields[16] = "15.5", "10.0", "-2.0", "3.0", "4.5"
        with patch.object(fetch_data, "get_text", return_value="\t".join(fields)):
            result = fetch_data.fetch_tic_cross_border_flows()
        self.assertEqual(result[0]["value_usd"], 15_500_000)
        self.assertEqual(result[-1]["value_usd"], 4_500_000)

    def test_parses_ici_weekly_flows(self):
        labels = ["Total equity", "Domestic", "World", "Hybrid", "Total bond", "Taxable", "Municipal", "Total"]
        text = "week ended Wednesday, August 26, 2026 " + " ".join(f"| {label} | 1,250" for label in labels)
        with patch.object(fetch_data, "get_page_text", return_value=text):
            result = fetch_data.fetch_ici_weekly_flows()
        self.assertGreaterEqual(len(result), 5)
        self.assertEqual(result[0]["value_usd"], 1_250_000_000)


class DerivedAnalyticsTests(unittest.TestCase):
    def test_news_summaries_do_not_require_model_api(self):
        groups = [[{
            "title": "Inflation cools as CPI misses forecasts",
            "summary": "Bond yields fell after the release.",
        }]]
        enriched, status = fetch_data.enrich_news_summaries(groups)
        self.assertEqual(status["status"], "local")
        self.assertIn("无需外部模型API", status["message"])
        self.assertIn("通胀", enriched[0][0]["summary_zh"])
        self.assertEqual(enriched[0][0]["summary_method"], "本地资产配置规则")

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
        history = [{"symbol": symbol, "points": points} for symbol in ("ACWI", "AGG", "DBC", "GLD", "UUP", "BOTZ", "EWH", "ASHR")]
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

