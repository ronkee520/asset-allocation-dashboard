from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from statistics import median
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "latest.json"
JS_PATH = DATA_DIR / "latest.js"
SECRET_DIR = ROOT / "APIkey与使用文档（链接）汇总"

USER_AGENT = "asset-allocation-dashboard/1.0"


KEY_FILES = {
    "FMP_API_KEY": "FMP.txt",
    "FRED_API_KEY": "FRED.txt",
    "EIA_API_KEY": "EIA.txt",
    "ALPHA_VANTAGE_API_KEY": "Alpha advantage.txt",
    "TWELVE_DATA_API_KEY": "Twelve Data.txt",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_previous() -> dict[str, Any]:
    if not JSON_PATH.exists():
        return {}
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def local_key(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value

    filename = KEY_FILES.get(name)
    if not filename:
        return ""
    path = SECRET_DIR / filename
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8", errors="ignore")
    candidates = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("http"):
            continue
        if "://" in clean:
            continue
        for token in re.split(r"[\s:=：,，;；]+", clean):
            token = token.strip().strip("\"'")
            if len(token) >= 12 and not token.lower().startswith("http"):
                candidates.append(token)
    return candidates[-1] if candidates else ""


def get_json(url: str, timeout: int = 25) -> Any:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def get_text(url: str, timeout: int = 35, referer: str = "") -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
        "Accept": "application/json,text/plain,text/csv,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        "Connection": "close",
    }
    if referer:
        headers["Referer"] = referer
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def post_json(url: str, payload: dict[str, Any], timeout: int = 40) -> Any:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        clean = " ".join(data.split())
        if clean:
            self.parts.append(clean)


def get_page_text(url: str, timeout: int = 35) -> str:
    if os.environ.get("SKIP_PRICING_NETWORK") == "1":
        raise URLError("pricing network disabled")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 asset-allocation-dashboard/1.0", "Accept": "text/html,*/*"})
    with urlopen(request, timeout=timeout) as response:
        parser = _VisibleTextParser()
        parser.feed(response.read().decode("utf-8", errors="replace"))
    text = " | ".join(parser.parts)
    if len(text) < 500:
        raise ValueError("pricing page has insufficient text")
    return text


def safe_source(previous: dict[str, Any], key: str, fetcher, fallback: Any) -> tuple[Any, dict[str, Any]]:
    started = time.time()
    try:
        data = fetcher()
        return data, {"key": key, "status": "online", "updated_at": now_iso(), "latency_ms": round((time.time() - started) * 1000)}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        old = previous.get(key)
        if old:
            return old, {"key": key, "status": "cached", "updated_at": previous.get("generated_at", ""), "message": type(exc).__name__}
        return fallback, {"key": key, "status": "fallback", "updated_at": now_iso(), "message": type(exc).__name__}


def as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def fetch_fmp_quotes() -> list[dict[str, Any]]:
    api_key = local_key("FMP_API_KEY")
    if not api_key:
        raise ValueError("missing FMP key")

    symbols = [
        "SPY", "QQQ", "TLT", "HYG", "GLD", "USO",
        "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META",
        "TSM", "ASML", "AMD", "JPM", "BOTZ", "VRT",
    ]
    rows = []
    for symbol in symbols:
        url = "https://financialmodelingprep.com/stable/quote?" + urlencode({"symbol": symbol, "apikey": api_key})
        try:
            item = get_json(url)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            time.sleep(0.5)
            continue
        if isinstance(item, list):
            rows.extend(item)
        elif isinstance(item, dict):
            rows.append(item)
        time.sleep(0.25)
    if not rows:
        raise ValueError("empty FMP quote response")
    output = []
    for row in rows:
        output.append({
            "symbol": row.get("symbol"),
            "name": row.get("name") or row.get("symbol"),
            "price": as_float(row.get("price")),
            "change_pct": as_float(row.get("changePercentage") if row.get("changePercentage") is not None else row.get("changesPercentage")),
            "volume": as_float(row.get("volume")),
            "avg_volume": as_float(row.get("avgVolume")),
            "pe": as_float(row.get("pe")),
            "price_avg_50": as_float(row.get("priceAvg50")),
            "price_avg_200": as_float(row.get("priceAvg200")),
            "market_cap": as_float(row.get("marketCap")),
            "exchange": row.get("exchange"),
            "source": "FMP",
            "url": f"https://financialmodelingprep.com/financial-summary/{row.get('symbol')}",
        })
    return [item for item in output if item["symbol"]]


def fetch_fred_series() -> list[dict[str, Any]]:
    api_key = local_key("FRED_API_KEY")
    if not api_key:
        raise ValueError("missing FRED key")

    series = [
        ("DGS10", "美国10年期国债收益率", "利率", "久期资产折现率、成长股估值、黄金机会成本"),
        ("DGS2", "美国2年期国债收益率", "利率", "政策利率预期、收益率曲线"),
        ("T10Y2Y", "美国10Y-2Y利差", "利率", "衰退预期、曲线修复、银行股压力"),
        ("FEDFUNDS", "联邦基金有效利率", "政策", "美元流动性和全球贴现率锚"),
        ("CPIAUCSL", "美国CPI同比", "通胀", "同比通胀方向、降息交易节奏"),
        ("UNRATE", "美国失业率", "就业", "经济周期与风险偏好"),
        ("BAMLH0A0HYM2", "美国高收益债利差", "信用", "信用风险偏好、权益下行保护"),
        ("INDPRO", "美国工业产出指数", "增长", "实体生产动能与经济周期方向"),
        ("PPIACO", "美国生产者价格指数", "通胀", "上游价格压力与商品周期验证"),
    ]
    output = []
    for series_id, name, category, driver in series:
        limit = 18 if series_id == "CPIAUCSL" else 2
        url = "https://api.stlouisfed.org/fred/series/observations?" + urlencode({
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        })
        payload = get_json(url, timeout=40)
        observations = payload.get("observations", [])
        clean = [obs for obs in observations if obs.get("value") not in (None, ".")]
        if not clean:
            continue
        latest = clean[0]
        previous = clean[1] if len(clean) > 1 else {}
        value = as_float(latest.get("value"))
        prev_value = as_float(previous.get("value"))
        if series_id == "CPIAUCSL" and len(clean) >= 14:
            year_ago = as_float(clean[12].get("value"))
            previous_year_ago = as_float(clean[13].get("value"))
            if value is not None and prev_value is not None and year_ago and previous_year_ago:
                value, prev_value = (value / year_ago - 1) * 100, (prev_value / previous_year_ago - 1) * 100
        change = value - prev_value if value is not None and prev_value is not None else None
        output.append({
            "series_id": series_id,
            "name": name,
            "category": category,
            "value": value,
            "previous": prev_value,
            "change": change,
            "date": latest.get("date"),
            "driver": driver,
            "source": "FRED",
            "url": f"https://fred.stlouisfed.org/series/{series_id}",
        })
        time.sleep(0.5)
    if not output:
        raise ValueError("empty FRED response")
    return output


def fetch_gdelt_news() -> list[dict[str, Any]]:
    query = "(AI OR semiconductor OR Nvidia OR oil OR gold OR central bank OR ETF OR inflation OR copper) market"
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode({
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 10,
        "sort": "hybridrel",
        "timespan": "48h",
    })
    payload = None
    last_error = None
    for delay in (0, 4, 10):
        if delay:
            time.sleep(delay)
        try:
            payload = get_json(url, timeout=40)
            break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
    if not isinstance(payload, dict):
        raise ValueError(f"GDELT unavailable: {type(last_error).__name__}")
    articles = payload.get("articles", [])
    output = []
    themes = ["AI", "半导体", "能源", "贵金属", "央行", "ETF", "通胀", "商品", "汇率", "宏观"]
    for index, article in enumerate(articles[:10]):
        title = article.get("title")
        link = article.get("url")
        if not title or not link:
            continue
        output.append({
            "theme": themes[index % len(themes)],
            "title": title,
            "source": article.get("domain") or article.get("sourceCountry") or "GDELT",
            "published_at": article.get("seendate", "")[:14],
            "url": link,
            "summary": "用于追踪跨资产价格波动背后的新闻叙事，点击可查看原文来源。",
        })
    if not output:
        raise ValueError("empty GDELT response")
    return output


def rule_news_summary_zh(item: dict[str, Any]) -> str:
    """Create a cautious Chinese allocation summary without an external model API."""
    title = str(item.get("title") or "").strip()
    summary = str(item.get("summary") or "").strip()
    text = f"{title} {summary}".lower()

    def has(*terms: str) -> bool:
        return any(term in text for term in terms)

    if has("inflation", " cpi", "通胀"):
        return "新闻聚焦通胀数据或预期变化，可能经由利率路径影响美债、美元、黄金及全球成长股估值。"
    if has("gold", "bullion", "黄金"):
        return "新闻关注黄金及其驱动因素，后续重点观察美元、实际利率、央行政策预期和避险需求。"
    if has("oil", "crude", "opec", "eia", "原油"):
        return "新闻涉及原油供需、库存或产量变化，可能影响油价、能源股表现以及市场对通胀的判断。"
    if has("fed", "fomc", "interest rate", "rate cut", "rate hike", "美联储"):
        return "报道关注美联储和利率路径，政策预期变化将影响美债收益率、美元、黄金及成长股估值。"
    if has("ai", "artificial intelligence", "semiconductor", "chip", "memory", "gpu", "半导体"):
        return "新闻涉及AI或半导体产业景气，需结合订单、资本开支、供需与估值，评估芯片、云计算及主题ETF影响。"
    if has("etf", "fund flow", "inflow", "outflow"):
        return "报道讨论ETF配置或资金动向，建议结合标的趋势、成交活跃度、份额变化和估算净申赎进一步判断。"
    if has("earnings", "results", "revenue", "profit", "guidance"):
        return "新闻聚焦公司业绩或经营指引，实际结果与管理层预期可能影响个股定价，并向所属行业传导。"
    if has("treasury", "bond", "yield", "美债"):
        return "报道关注债券收益率或利率预期变化，可能影响美元、黄金、权益估值及跨资产风险偏好。"
    if has("copper", "commodity", "commodities", "铜", "商品"):
        return "新闻涉及工业品或大宗商品，需结合供需、库存、美元和全球增长预期判断周期资产配置影响。"
    if has("china", "chinese", "hong kong", "中国", "港股", "a股"):
        return "新闻关注中国相关市场或政策变化，可能影响A股、港股、人民币以及全球周期和消费板块情绪。"
    if has("s&p 500", "stock", "stocks", "market", "markets", "equity"):
        return "报道反映权益市场或个股线索，需结合估值、盈利趋势和宏观环境判断其对整体风险偏好的影响。"

    short_title = re.sub(r"\s+", " ", title)[:72]
    return f"该报道聚焦“{short_title or '全球市场动态'}”，建议结合原文、行情变化及相关资产基本面判断其配置影响。"


def enrich_news_summaries(news_groups: list[list[dict[str, Any]]]) -> tuple[list[list[dict[str, Any]]], dict[str, Any]]:
    """Attach deterministic Chinese summaries without requiring an API key."""
    flat = [item for group in news_groups for item in group if item.get("title")]
    for item in flat:
        item["summary_zh"] = rule_news_summary_zh(item)
        item["summary_method"] = "本地资产配置规则"
    return news_groups, {
        "key": "news_summary_zh",
        "status": "local",
        "updated_at": now_iso(),
        "message": f"本地规则摘要 {len(flat)} 条；无需外部模型API",
    }


def fetch_alpha_news() -> list[dict[str, Any]]:
    api_key = local_key("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError("missing Alpha Vantage key")
    url = "https://www.alphavantage.co/query?" + urlencode({
        "function": "NEWS_SENTIMENT",
        "topics": "technology,financial_markets,economy_macro",
        "sort": "LATEST",
        "limit": 10,
        "apikey": api_key,
    })
    payload = get_json(url)
    feed = payload.get("feed", [])
    output = []
    for item in feed[:8]:
        output.append({
            "theme": "市场情绪",
            "title": item.get("title"),
            "source": item.get("source"),
            "published_at": item.get("time_published"),
            "url": item.get("url"),
            "summary": item.get("summary", "")[:180],
            "sentiment": item.get("overall_sentiment_label"),
            "score": as_float(item.get("overall_sentiment_score")),
        })
    output = [item for item in output if item.get("title") and item.get("url")]
    if not output:
        raise ValueError("empty Alpha news response")
    return output


def fetch_eia_energy() -> list[dict[str, Any]]:
    api_key = local_key("EIA_API_KEY")
    if not api_key:
        raise ValueError("missing EIA key")
    url = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/?" + urlencode({
        "api_key": api_key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": "WCESTUS1",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "offset": 0,
        "length": 2,
    })
    payload = get_json(url)
    rows = payload.get("response", {}).get("data", [])
    if not rows:
        raise ValueError("empty EIA response")
    output = []
    for row in rows[:2]:
        output.append({
            "series_id": row.get("series"),
            "name": "美国商业原油库存",
            "category": "能源库存",
            "period": row.get("period"),
            "value": as_float(row.get("value")),
            "unit": row.get("units"),
            "driver": "原油库存影响油价、通胀预期与能源股配置",
            "source": "EIA",
            "url": "https://www.eia.gov/petroleum/supply/weekly/",
        })
    return output


def fetch_twelve_fx() -> list[dict[str, Any]]:
    api_key = local_key("TWELVE_DATA_API_KEY")
    if not api_key:
        raise ValueError("missing Twelve Data key")
    symbols = "USD/CNH,EUR/USD,USD/JPY"
    url = "https://api.twelvedata.com/quote?" + urlencode({"symbol": symbols, "apikey": api_key})
    payload = get_json(url)
    if not isinstance(payload, dict) or payload.get("status") == "error":
        raise ValueError("bad Twelve Data response")
    rows = payload.values() if all(isinstance(v, dict) for v in payload.values()) else [payload]
    output = []
    for row in rows:
        output.append({
            "symbol": row.get("symbol"),
            "name": row.get("name") or row.get("symbol"),
            "price": as_float(row.get("close")),
            "change_pct": as_float(row.get("percent_change")),
            "previous_close": as_float(row.get("previous_close")),
            "source": "Twelve Data",
            "url": "https://twelvedata.com/",
        })
    output = [item for item in output if item.get("symbol")]
    if not output:
        raise ValueError("empty Twelve Data response")
    return output


def fetch_market_history() -> list[dict[str, Any]]:
    """Fetch daily adjusted closes from Yahoo's public chart endpoint.

    The ETF proxies keep the cross-asset matrix comparable across regions and
    avoid consuming any of the metered API quotas.
    """
    symbols = [
        ("SPY", "美股", "S&P 500 ETF"),
        ("ASHR", "A股", "沪深300 ETF"),
        ("EWH", "港股", "香港市场 ETF"),
        ("GLD", "黄金", "黄金 ETF"),
        ("UUP", "美元", "美元指数 ETF"),
        ("TLT", "美债", "20年期美债 ETF"),
        ("CPER", "铜", "铜期货 ETF"),
        ("USO", "原油", "原油 ETF"),
        ("BOTZ", "AI", "机器人与AI ETF"),
    ]
    output = []
    for symbol, label, name in symbols:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d&events=history"
        payload = get_json(url, timeout=35)
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            continue
        timestamps = result.get("timestamp") or []
        closes = ((result.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
                  or (result.get("indicators", {}).get("quote") or [{}])[0].get("close")
                  or [])
        points = []
        for timestamp, close in zip(timestamps, closes):
            value = as_float(close)
            if value is None:
                continue
            points.append({
                "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
                "close": value,
            })
        if len(points) >= 20:
            output.append({
                "symbol": symbol,
                "label": label,
                "name": name,
                "points": points[-126:],
                "source": "Yahoo Finance",
                "url": f"https://finance.yahoo.com/quote/{symbol}/history/",
            })
        time.sleep(0.35)
    if len(output) < 6:
        raise ValueError("insufficient market history")
    return output


COMMODITY_SPECS = [
    ("GC=F", "黄金", "贵金属", "COMEX", "美元/盎司", "https://finance.yahoo.com/quote/GC=F/"),
    ("SI=F", "白银", "贵金属", "COMEX", "美元/盎司", "https://finance.yahoo.com/quote/SI=F/"),
    ("PL=F", "铂金", "贵金属", "NYMEX", "美元/盎司", "https://finance.yahoo.com/quote/PL=F/"),
    ("PA=F", "钯金", "贵金属", "NYMEX", "美元/盎司", "https://finance.yahoo.com/quote/PA=F/"),
    ("HG=F", "铜", "工业金属", "COMEX", "美元/磅", "https://finance.yahoo.com/quote/HG=F/"),
    ("ALI=F", "铝", "工业金属", "COMEX", "美元/吨", "https://finance.yahoo.com/quote/ALI=F/"),
    ("CL=F", "WTI原油", "能源", "NYMEX", "美元/桶", "https://finance.yahoo.com/quote/CL=F/"),
    ("BZ=F", "布伦特原油", "能源", "ICE", "美元/桶", "https://finance.yahoo.com/quote/BZ=F/"),
    ("NG=F", "天然气", "能源", "NYMEX", "美元/MMBtu", "https://finance.yahoo.com/quote/NG=F/"),
    ("HO=F", "取暖油", "能源", "NYMEX", "美元/加仑", "https://finance.yahoo.com/quote/HO=F/"),
    ("ZC=F", "玉米", "谷物", "CBOT", "美分/蒲式耳", "https://finance.yahoo.com/quote/ZC=F/"),
    ("ZW=F", "小麦", "谷物", "CBOT", "美分/蒲式耳", "https://finance.yahoo.com/quote/ZW=F/"),
    ("ZS=F", "大豆", "谷物", "CBOT", "美分/蒲式耳", "https://finance.yahoo.com/quote/ZS=F/"),
    ("KC=F", "咖啡", "软商品", "ICE", "美分/磅", "https://finance.yahoo.com/quote/KC=F/"),
    ("SB=F", "原糖", "软商品", "ICE", "美分/磅", "https://finance.yahoo.com/quote/SB=F/"),
    ("CT=F", "棉花", "软商品", "ICE", "美分/磅", "https://finance.yahoo.com/quote/CT=F/"),
    ("CC=F", "可可", "软商品", "ICE", "美元/吨", "https://finance.yahoo.com/quote/CC=F/"),
    ("LE=F", "活牛", "畜牧", "CME", "美分/磅", "https://finance.yahoo.com/quote/LE=F/"),
    ("LBS=F", "木材", "建材", "CME", "美元/千板英尺", "https://finance.yahoo.com/quote/LBS=F/"),
]

CHINA_COMMODITY_SPECS = [
    ("RB0", "RB", "螺纹钢", "黑色系", "上期所", "元/吨", "https://finance.sina.com.cn/futures/quotes/RB0.shtml"),
    ("HC0", "HC", "热轧卷板", "黑色系", "上期所", "元/吨", "https://finance.sina.com.cn/futures/quotes/HC0.shtml"),
    ("I0", "I", "铁矿石", "黑色系", "大商所", "元/吨", "https://finance.sina.com.cn/futures/quotes/I0.shtml"),
]


def parse_sina_futures_jsonp(text: str) -> list[dict[str, Any]]:
    payload_match = re.search(r"=\s*\(?(\[.*\])\)?\s*;?\s*$", text, re.DOTALL)
    if not payload_match:
        raise ValueError("missing Sina futures JSONP payload")
    return json.loads(payload_match.group(1))


def _changes_and_risk(points: list[dict[str, Any]]) -> dict[str, float | None]:
    closes = [as_float(item.get("close")) for item in points]
    closes = [value for value in closes if value is not None]

    def change(days: int) -> float | None:
        if len(closes) <= days or not closes[-days - 1]:
            return None
        return (closes[-1] / closes[-days - 1] - 1) * 100

    returns = [closes[index] / closes[index - 1] - 1 for index in range(1, len(closes)) if closes[index - 1]]
    recent = returns[-20:]
    volatility = None
    if len(recent) >= 5:
        mean = sum(recent) / len(recent)
        variance = sum((value - mean) ** 2 for value in recent) / len(recent)
        volatility = math.sqrt(variance) * math.sqrt(252) * 100
    low, high = (min(closes), max(closes)) if closes else (None, None)
    percentile = None
    if closes and high is not None and low is not None:
        percentile = 50.0 if high == low else (closes[-1] - low) / (high - low) * 100
    return {
        "change_1d": change(1),
        "change_20d": change(20),
        "change_60d": change(60),
        "volatility_20d": volatility,
        "range_percentile": percentile,
        "range_low": low,
        "range_high": high,
    }


def fetch_commodity_market(previous_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    previous_map = {str(row.get("symbol")): row for row in (previous_rows or [])}
    output: list[dict[str, Any]] = []
    for symbol, name, category, market, unit, source_url in COMMODITY_SPECS:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1y&interval=1d&events=history"
            payload = get_json(url, timeout=35)
            result = (payload.get("chart", {}).get("result") or [None])[0]
            if not result:
                continue
            timestamps = result.get("timestamp") or []
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            closes = quote.get("close") or []
            volumes = quote.get("volume") or []
            points = []
            for index, (timestamp, close) in enumerate(zip(timestamps, closes)):
                value = as_float(close)
                if value is None:
                    continue
                points.append({
                    "date": datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat(),
                    "close": value,
                    "volume": as_float(volumes[index]) if index < len(volumes) else None,
                })
            if len(points) < 20:
                continue
            output.append({
                "symbol": symbol,
                "name": name,
                "category": category,
                "market": market,
                "unit": unit,
                "price": points[-1]["close"],
                "volume": points[-1].get("volume"),
                "as_of": points[-1]["date"],
                "source": "Yahoo Finance公开日线",
                "source_type": "公开行情",
                "url": source_url,
                "history": points[-252:],
                **_changes_and_risk(points[-252:]),
            })
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError):
            cached = previous_map.get(symbol)
            if cached:
                output.append({**cached, "data_status": "cached"})
        time.sleep(0.2)

    for api_symbol, symbol, name, category, market, unit, source_url in CHINA_COMMODITY_SPECS:
        try:
            text = get_text(
                "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
                f"var%20_{api_symbol}=/InnerFuturesNewService.getDailyKLine?symbol={api_symbol}",
                timeout=40,
                referer="https://finance.sina.com.cn/",
            )
            lines = parse_sina_futures_jsonp(text)
            points = []
            for item in lines:
                close = as_float(item.get("c"))
                if close is None:
                    continue
                points.append({"date": str(item.get("d", "")), "close": close, "volume": as_float(item.get("v"))})
            if len(points) < 20:
                continue
            output.append({
                "symbol": symbol,
                "name": name,
                "category": category,
                "market": market,
                "unit": unit,
                "price": points[-1]["close"],
                "volume": points[-1].get("volume"),
                "as_of": points[-1]["date"],
                "source": "新浪财经连续期货日线",
                "source_type": "公开行情",
                "url": source_url,
                "history": points[-252:],
                **_changes_and_risk(points[-252:]),
            })
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            cached = previous_map.get(symbol)
            if cached:
                output.append({**cached, "data_status": "cached"})
        time.sleep(0.45)
    if len(output) < 12:
        raise ValueError("insufficient commodity market data")
    return output


CFTC_MARKETS = [
    ("GOLD", "黄金"), ("SILVER", "白银"), ("COPPER", "铜"),
    ("CRUDE OIL, LIGHT SWEET", "WTI原油"), ("NATURAL GAS", "天然气"),
    ("CORN", "玉米"), ("SOYBEANS", "大豆"), ("WHEAT-SRW", "小麦"),
    ("COFFEE C", "咖啡"), ("SUGAR NO. 11", "原糖"), ("COTTON NO. 2", "棉花"),
    ("COCOA", "可可"), ("LIVE CATTLE", "活牛"),
]


def fetch_cftc_positions() -> list[dict[str, Any]]:
    text = get_text("https://www.cftc.gov/dea/newcot/f_disagg.txt", timeout=45)
    rows = list(csv.reader(io.StringIO(text)))
    output = []
    for contract_prefix, display_name in CFTC_MARKETS:
        row = next((item for item in rows if item and item[0].strip().upper().startswith(contract_prefix)), None)
        if not row or len(row) < 79:
            continue
        long_position = as_float(row[13])
        short_position = as_float(row[14])
        open_interest = as_float(row[7])
        change_long = as_float(row[61])
        change_short = as_float(row[62])
        if long_position is None or short_position is None:
            continue
        net = long_position - short_position
        weekly_change = (change_long or 0) - (change_short or 0)
        output.append({
            "name": display_name,
            "contract": row[0].strip(),
            "as_of": row[2].strip(),
            "open_interest": open_interest,
            "managed_money_long": long_position,
            "managed_money_short": short_position,
            "managed_money_net": net,
            "weekly_change": weekly_change,
            "net_pct_open_interest": net / open_interest * 100 if open_interest else None,
            "source": "CFTC Disaggregated COT",
            "frequency": "周频",
            "url": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
        })
    if len(output) < 8:
        raise ValueError("insufficient CFTC positions")
    return output


AI_CHAIN_GROUPS = [
    ("上游", "GPU / HBM", ["NVDA", "AMD", "MU", "AVGO"], "GPU、HBM与高速互连决定训练和推理基础设施供给"),
    ("上游", "晶圆 / 设备", ["TSM", "ASML", "AMAT", "LRCX"], "先进制程扩产与设备订单反映算力资本开支兑现"),
    ("中游", "云与算力平台", ["MSFT", "GOOGL", "AMZN", "ORCL"], "云增速、AI订单和资本开支回报率共同决定景气"),
    ("中游", "电力 / 电网", ["CEG", "ETN", "PWR"], "数据中心负荷推动电源、电网与工程投资"),
    ("中游", "液冷 / 热管理", ["VRT", "MOD"], "高功率机柜提升液冷渗透率和单柜价值量"),
    ("下游", "应用 / SaaS", ["PLTR", "CRM", "NOW"], "关注AI产品付费转化、席位扩张和利润兑现"),
    ("下游", "机器人", ["BOTZ", "ISRG"], "订单、自动化渗透率与量产节奏决定主题持续性"),
    ("材料", "铜 / 稀土材料", ["FCX", "SCCO", "MP"], "电气化需求与资源供给约束共同影响材料价值"),
]


def fetch_ai_chain_quotes(base_quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill free-plan quote gaps with Yahoo daily chart data."""
    base_map = {str(item.get("symbol")): dict(item) for item in base_quotes}
    symbols = sorted({symbol for _, _, group_symbols, _ in AI_CHAIN_GROUPS for symbol in group_symbols})
    def fetch_symbol(symbol: str) -> dict[str, Any] | None:
        payload = None
        url = f"https://finance.yahoo.com/quote/{symbol}/"
        for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
            try:
                payload = get_json(f"https://{host}/v8/finance/chart/{symbol}?range=1mo&interval=1d&events=history", timeout=35)
                break
            except (HTTPError, URLError, TimeoutError, OSError, ValueError):
                continue
        if not isinstance(payload, dict):
            return None
        result = (payload.get("chart", {}).get("result") or [None])[0]
        if not result:
            return None
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        closes = [as_float(value) for value in quote.get("close") or []]
        volumes = [as_float(value) for value in quote.get("volume") or []]
        valid_closes = [value for value in closes if value is not None]
        valid_volumes = [value for value in volumes[-21:-1] if value is not None]
        if len(valid_closes) < 2:
            return None
        row = {
            "symbol": symbol, "name": symbol, "price": valid_closes[-1],
            "change_pct": (valid_closes[-1] / valid_closes[-2] - 1) * 100,
            "volume": next((value for value in reversed(volumes) if value is not None), None),
            "avg_volume": sum(valid_volumes) / len(valid_volumes) if valid_volumes else None,
            "pe": None, "source": "Yahoo Finance", "url": url,
        }
        preferred = base_map.get(symbol, {})
        for key, value in preferred.items():
            if value is not None:
                row[key] = value
        return row

    output = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            row = future.result()
            if row:
                output.append(row)
    output.sort(key=lambda item: str(item.get("symbol")))
    if len(output) < 12:
        raise ValueError("insufficient AI chain quote coverage")
    return output


def fetch_ai_valuations(previous_rows: list[dict[str, Any]], previous_generated_at: str = "") -> list[dict[str, Any]]:
    """Refresh TTM P/E once daily to preserve FMP's 250-call free allowance."""
    today = datetime.now(timezone.utc).date().isoformat()
    if previous_rows and previous_generated_at[:10] == today:
        return previous_rows
    api_key = local_key("FMP_API_KEY")
    if not api_key:
        raise ValueError("missing FMP key")
    symbols = sorted({symbol for _, _, group_symbols, _ in AI_CHAIN_GROUPS for symbol in group_symbols})
    def fetch_symbol(symbol: str) -> dict[str, Any] | None:
        url = "https://financialmodelingprep.com/stable/ratios-ttm?" + urlencode({"symbol": symbol, "apikey": api_key})
        try:
            payload = get_json(url, timeout=30)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            return None
        row = payload[0] if isinstance(payload, list) and payload else payload if isinstance(payload, dict) else {}
        pe = as_float(row.get("priceToEarningsRatioTTM"))
        if pe is not None and 0 < pe < 300:
            return {"symbol": symbol, "pe": round(pe, 3), "as_of": today, "source": "FMP ratios-ttm"}
        return None

    output = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            row = future.result()
            if row:
                output.append(row)
    output.sort(key=lambda item: str(item.get("symbol")))
    if len(output) < 5:
        raise ValueError("insufficient AI valuation coverage")
    return output


def build_ai_chain_metrics(quotes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    quote_map = {str(item.get("symbol")): item for item in quotes}
    output = []
    for segment, group, symbols, signal in AI_CHAIN_GROUPS:
        rows = [quote_map[symbol] for symbol in symbols if symbol in quote_map and as_float(quote_map[symbol].get("change_pct")) is not None]
        if not rows:
            continue
        changes = [as_float(row.get("change_pct")) or 0 for row in rows]
        relative_volumes, valuations, turnovers = [], [], []
        for row in rows:
            volume, avg_volume, price, pe = (as_float(row.get(key)) for key in ("volume", "avg_volume", "price", "pe"))
            if volume and avg_volume:
                relative_volumes.append(volume / avg_volume)
            if pe and 0 < pe < 300:
                valuations.append(pe)
            if volume and price:
                turnovers.append(volume * price)
        change = sum(changes) / len(changes)
        breadth = sum(value > 0 for value in changes) / len(changes) * 100
        relative_volume = sum(relative_volumes) / len(relative_volumes) if relative_volumes else 1
        valuation = median(valuations) if valuations else None
        raw_strength = max(35, min(95, 55 + change * 5 + (relative_volume - 1) * 12 + (breadth - 50) * 0.24))
        leaders = sorted(rows, key=lambda item: as_float(item.get("change_pct")) or -999, reverse=True)
        output.append({
            "segment": segment, "group": group, "constituents": " · ".join(symbols),
            "leaders": " · ".join(str(item.get("symbol")) for item in leaders[:3]),
            "change": round(change, 3), "breadth": round(breadth, 1), "relative_volume": round(relative_volume, 2),
            "valuation_pe": round(valuation, 1) if valuation is not None else None,
            "turnover_usd": round(sum(turnovers)), "strength": round(raw_strength), "raw_strength": raw_strength, "signal": signal,
            "sample_size": len(rows), "method": "成分股行情自动计算", "as_of": now_iso(),
        })
    if output:
        low = min(item["raw_strength"] for item in output)
        high = max(item["raw_strength"] for item in output)
        spread = high - low
        for item in output:
            raw = item.pop("raw_strength")
            item["strength"] = round(max(62, min(88, raw))) if spread < 1 else round(62 + (raw - low) / spread * 26)
    return output


def _series_raw_scores(points: list[dict[str, Any]]) -> list[tuple[int, float]]:
    closes = [as_float(item.get("close")) for item in points]
    output = []
    for index in range(60, len(closes)):
        if any(value is None or value <= 0 for value in (closes[index], closes[index - 20], closes[index - 60])):
            continue
        daily = [closes[i] / closes[i - 1] - 1 for i in range(index - 19, index + 1) if closes[i] and closes[i - 1]]
        if len(daily) < 18:
            continue
        mean = sum(daily) / len(daily)
        volatility = (sum((value - mean) ** 2 for value in daily) / len(daily)) ** 0.5 * (252 ** 0.5) * 100
        momentum20 = (closes[index] / closes[index - 20] - 1) * 100
        momentum60 = (closes[index] / closes[index - 60] - 1) * 100
        output.append((index, momentum20 * 1.5 + momentum60 * 0.6 - volatility * 0.12))
    return output


def build_score_backtest(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    asset_map = {"股票": "SPY", "债券": "TLT", "商品": "CPER", "黄金": "GLD", "美元": "UUP", "AI": "BOTZ", "港股": "EWH", "A股": "ASHR"}
    series_map = {str(item.get("symbol")): item for item in history}
    output = []
    for asset, symbol in asset_map.items():
        series = series_map.get(symbol)
        if not series:
            continue
        points = series.get("points") or []
        closes = [as_float(item.get("close")) for item in points]
        scores = _series_raw_scores(points)
        if len(scores) < 10:
            continue
        raw_values = [value for _, value in scores]
        current_raw = raw_values[-1]
        current_percentile = sum(value <= current_raw for value in raw_values) / len(raw_values) * 100
        ranked = sorted(raw_values)
        threshold = ranked[max(0, int(len(ranked) * 0.6) - 1)]
        observations = []
        for index, raw in scores:
            if raw < threshold or index + 20 >= len(closes) or not closes[index] or not closes[index + 20]:
                continue
            observations.append((closes[index + 20] / closes[index] - 1) * 100)
        peak, max_drawdown = 0.0, 0.0
        for close in (value for value in closes if value is not None):
            peak = max(peak, close)
            if peak:
                max_drawdown = min(max_drawdown, (close / peak - 1) * 100)
        output.append({
            "asset": asset, "symbol": symbol, "sample_size": len(observations),
            "hit_rate_20d": round(sum(value > 0 for value in observations) / len(observations) * 100, 1) if observations else None,
            "avg_forward_return_20d": round(sum(observations) / len(observations), 2) if observations else None,
            "max_drawdown": round(max_drawdown, 2), "current_percentile": round(current_percentile, 1),
            "history_days": len(points), "method": "60日内技术信号达到历史前40%后，检验未来20日收益；无前视数据",
        })
    return output


FRED_EVENT_MAP = {
    "Consumer Price Index": ("美国CPI", "高", "全球股债、美元、黄金"),
    "Employment Situation": ("美国非农就业报告", "高", "美债、美元、黄金、美股"),
    "Producer Price Index": ("美国PPI", "高", "美债、美元、商品、成长股"),
    "Gross Domestic Product": ("美国GDP", "高", "美股、美债、美元、商品"),
    "Personal Income and Outlays": ("美国PCE通胀与个人支出", "高", "全球股债、美元、黄金"),
    "Advance Monthly Sales for Retail and Food Services": ("美国零售销售", "中", "美股、美债、美元"),
    "Industrial Production and Capacity Utilization": ("美国工业生产", "中", "美股、铜、美元"),
}


def fetch_event_calendar() -> list[dict[str, Any]]:
    api_key = local_key("FRED_API_KEY")
    if not api_key:
        raise ValueError("missing FRED key")
    today = datetime.now(timezone.utc).date()
    end = today + timedelta(days=180)
    url = "https://api.stlouisfed.org/fred/releases/dates?" + urlencode({
        "api_key": api_key, "file_type": "json", "realtime_start": today.isoformat(),
        "realtime_end": end.isoformat(), "include_release_dates_with_no_data": "true",
        "sort_order": "asc", "limit": 1000,
    })
    payload = get_json(url, timeout=35)
    output, seen = [], set()
    for item in payload.get("release_dates", []):
        mapped = FRED_EVENT_MAP.get(str(item.get("release_name")))
        date = str(item.get("date") or "")
        if not mapped or not date or (date, mapped[0]) in seen:
            continue
        seen.add((date, mapped[0]))
        output.append({"date": date, "region": "美国", "event": mapped[0], "importance": mapped[1], "assets": mapped[2], "source": "https://fred.stlouisfed.org/releases/calendar", "source_name": "FRED官方发布日历"})

    try:
        fed_url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
        fed_text = get_page_text(fed_url, timeout=40)
        month_numbers = {name: index for index, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
        for year in (today.year, today.year + 1):
            section_match = re.search(rf"{year}\s+FOMC Meetings\s*\|(.+?)(?=\|\s*\d{{4}}\s+FOMC Meetings|\|\s*Note:)", fed_text, re.IGNORECASE)
            if not section_match:
                continue
            for month_name, _start_day, decision_day in re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s*\|\s*(\d{1,2})-(\d{1,2})\*?", section_match.group(1)):
                date = f"{year}-{month_numbers[month_name]:02d}-{int(decision_day):02d}"
                if date < today.isoformat() or (date, "FOMC利率决议") in seen:
                    continue
                seen.add((date, "FOMC利率决议"))
                output.append({"date": date, "region": "美国", "event": "FOMC利率决议", "importance": "高", "assets": "全球股债、美元、黄金、汇率", "source": fed_url, "source_name": "美联储官方会议日历"})
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        pass

    output.sort(key=lambda item: (item["date"], item["event"]))
    if not output:
        raise ValueError("empty FRED event calendar")
    return output[:60]


ETF_FUND_SOURCES = [
    {
        "symbol": "SPY",
        "asset": "美股",
        "asset_class": "股票",
        "region": "美国",
        "segment": "大盘",
        "issuer": "State Street",
        "parser": "ssga",
        "url": "https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy",
    },
    {
        "symbol": "GLD",
        "asset": "黄金",
        "asset_class": "商品",
        "region": "全球",
        "segment": "贵金属",
        "issuer": "State Street",
        "parser": "ssga",
        "url": "https://www.ssga.com/us/en/individual/etfs/spdr-gold-shares-gld",
    },
    {
        "symbol": "TLT",
        "asset": "美债",
        "asset_class": "债券",
        "region": "美国",
        "segment": "长期国债",
        "issuer": "iShares",
        "parser": "ishares",
        "url": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
    },
    {
        "symbol": "EWH",
        "asset": "港股",
        "asset_class": "股票",
        "region": "中国香港",
        "segment": "综合",
        "issuer": "iShares",
        "parser": "ishares",
        "url": "https://www.ishares.com/us/products/239657/ishares-msci-hong-kong-etf",
    },
    {
        "symbol": "BOTZ",
        "asset": "AI",
        "asset_class": "股票",
        "region": "全球",
        "segment": "AI主题",
        "issuer": "Global X",
        "parser": "globalx",
        "url": "https://www.globalxetfs.com/funds/botz",
    },
    {
        "symbol": "IVV", "asset": "美股大盘", "asset_class": "股票", "region": "美国", "segment": "大盘",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf",
    },
    {
        "symbol": "IWM", "asset": "美股小盘", "asset_class": "股票", "region": "美国", "segment": "小盘",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf",
    },
    {
        "symbol": "IEFA", "asset": "发达市场", "asset_class": "股票", "region": "发达市场(除美国)", "segment": "综合",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/244049/ishares-core-msci-eafe-etf",
    },
    {
        "symbol": "EEM", "asset": "新兴市场", "asset_class": "股票", "region": "新兴市场", "segment": "综合",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239637/ishares-msci-emerging-markets-etf",
    },
    {
        "symbol": "EWJ", "asset": "日本股市", "asset_class": "股票", "region": "日本", "segment": "综合",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239665/ishares-msci-japan-etf",
    },
    {
        "symbol": "MCHI", "asset": "中国股票", "asset_class": "股票", "region": "中国", "segment": "综合",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239619/ishares-msci-china-etf",
    },
    {
        "symbol": "INDA", "asset": "印度股市", "asset_class": "股票", "region": "印度", "segment": "综合",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239659/ishares-msci-india-etf",
    },
    {
        "symbol": "AGG", "asset": "美国综合债", "asset_class": "债券", "region": "美国", "segment": "综合债",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239458/ishares-core-total-us-bond-market-etf",
    },
    {
        "symbol": "HYG", "asset": "美国高收益债", "asset_class": "债券", "region": "美国", "segment": "高收益债",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf",
    },
    {
        "symbol": "EMB", "asset": "新兴市场债", "asset_class": "债券", "region": "新兴市场", "segment": "主权债",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239572/ishares-jp-morgan-usd-emerging-markets-bond-etf",
    },
    {
        "symbol": "SLV", "asset": "白银", "asset_class": "商品", "region": "全球", "segment": "贵金属",
        "issuer": "iShares", "parser": "ishares", "url": "https://www.ishares.com/us/products/239855/ishares-silver-trust-fund",
    },
]


def _number(text: str) -> float:
    return float(text.replace(",", "").replace("$", "").strip())


def _iso_fund_date(text: str) -> str:
    clean = text.replace(",", "").strip()
    return datetime.strptime(clean, "%b %d %Y").date().isoformat()


def parse_etf_fund_page(text: str, parser: str) -> dict[str, Any]:
    if parser == "ssga":
        match = re.search(
            r"Fund Net Asset Value\s*\|\s*as of\s+([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}).{0,500}?"
            r"\|\s*\$([0-9,.]+)\s*\|\s*Shares Outstanding\s*\|\s*([0-9,.]+)\s*M",
            text,
            re.IGNORECASE,
        )
        if not match:
            raise ValueError("missing State Street ETF fields")
        as_of, nav, shares_m = match.groups()
        return {"as_of": _iso_fund_date(as_of), "nav": _number(nav), "shares_outstanding": round(_number(shares_m) * 1_000_000)}

    if parser == "ishares":
        shares_match = re.search(
            r"Shares Outstanding\s*\|\s*([0-9,.]+)\s*\|\s*as of\s*\|?\s*([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})",
            text,
            re.IGNORECASE,
        )
        nav_match = re.search(r'NAV as of","value":"([0-9,.]+)".{0,260}?"value":"([A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})"', text)
        if not shares_match or not nav_match:
            raise ValueError("missing iShares ETF fields")
        shares, shares_date = shares_match.groups()
        nav, nav_date = nav_match.groups()
        as_of = min(_iso_fund_date(shares_date), _iso_fund_date(nav_date))
        return {"as_of": as_of, "nav": _number(nav), "shares_outstanding": round(_number(shares))}

    if parser == "globalx":
        key_match = re.search(
            r"Key Information\s*\|\s*As of\s*\|\s*([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}).{0,500}?"
            r"Net Assets\s*\|\s*\$[0-9,.]+\s+(?:million|billion)\s*\|\s*NAV\s*\|\s*\$\s*\|\s*([0-9,.]+)",
            text,
            re.IGNORECASE,
        )
        shares_match = re.search(r"Trading Details.{0,700}?Shares Outstanding\s*\|\s*([0-9,.]+)", text, re.IGNORECASE)
        if not key_match or not shares_match:
            raise ValueError("missing Global X ETF fields")
        as_of, nav = key_match.groups()
        return {"as_of": _iso_fund_date(as_of), "nav": _number(nav), "shares_outstanding": round(_number(shares_match.group(1)))}

    raise ValueError(f"unsupported ETF parser: {parser}")


def fetch_etf_fund_flows(previous_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    previous_map = {str(row.get("symbol")): row for row in (previous_rows or [])}
    output = []
    for source in ETF_FUND_SOURCES:
        previous = previous_map.get(str(source["symbol"]), {})
        current = None
        for attempt in range(2):
            try:
                text = get_page_text(str(source["url"]), timeout=45)
                current = parse_etf_fund_page(text, str(source["parser"]))
                current["shares_outstanding"] = round(current["shares_outstanding"])
                break
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
                if attempt == 0:
                    time.sleep(1.2)
        if current is None:
            if previous:
                cached = dict(previous)
                cached.update({key: source[key] for key in ("asset", "asset_class", "region", "segment", "issuer")})
                cached["data_status"] = "cached"
                output.append(cached)
            continue
        history = list(previous.get("history") or [])
        previous_snapshot = {
            "date": previous.get("as_of"),
            "nav": previous.get("nav"),
            "shares_outstanding": previous.get("shares_outstanding"),
        }
        if previous_snapshot["date"] and previous_snapshot["shares_outstanding"] is not None:
            history.append(previous_snapshot)
        history.append({
            "date": current["as_of"],
            "nav": current["nav"],
            "shares_outstanding": current["shares_outstanding"],
        })
        by_date = {str(item.get("date")): item for item in history if item.get("date")}
        history = [by_date[key] for key in sorted(by_date)][-31:]

        shares_change = None
        shares_change_pct = None
        estimated_flow = None
        if len(history) >= 2:
            prior = history[-2]
            prior_shares = as_float(prior.get("shares_outstanding"))
            if prior_shares and history[-1]["date"] != prior["date"]:
                shares_change = current["shares_outstanding"] - prior_shares
                shares_change_pct = shares_change / prior_shares * 100
                estimated_flow = shares_change * current["nav"]

        def cumulative_flow(days: int) -> float | None:
            selected = history[-(days + 1):]
            if len(selected) < 2:
                return None
            total = 0.0
            observations = 0
            for prior, latest in zip(selected, selected[1:]):
                prior_shares = as_float(prior.get("shares_outstanding"))
                latest_shares = as_float(latest.get("shares_outstanding"))
                latest_nav = as_float(latest.get("nav"))
                if prior_shares is None or latest_shares is None or latest_nav is None:
                    continue
                total += (latest_shares - prior_shares) * latest_nav
                observations += 1
            return total if observations else None

        aum = current["shares_outstanding"] * current["nav"]

        output.append({
            "symbol": source["symbol"],
            "asset": source["asset"],
            "asset_class": source["asset_class"],
            "region": source["region"],
            "segment": source["segment"],
            "issuer": source["issuer"],
            "as_of": current["as_of"],
            "nav": current["nav"],
            "shares_outstanding": current["shares_outstanding"],
            "shares_change": shares_change,
            "shares_change_pct": shares_change_pct,
            "estimated_flow": estimated_flow,
            "flow_5d": cumulative_flow(5),
            "flow_20d": cumulative_flow(20),
            "aum": aum,
            "flow_intensity": estimated_flow / aum * 100 if estimated_flow is not None and aum else None,
            "method": "发行商流通份额变化 × 当日NAV",
            "source": "基金发行商官网",
            "data_status": "online",
            "url": source["url"],
            "history": history,
        })
        time.sleep(0.35)
    if len(output) < 5:
        raise ValueError("insufficient official ETF fund data")
    return output


def fetch_ici_weekly_flows() -> list[dict[str, Any]]:
    url = "https://www.ici.org/research/stats/flows"
    text = get_page_text(url, timeout=45)
    date_match = re.search(r"week ended Wednesday,\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})", text)
    as_of = datetime.strptime(date_match.group(1), "%B %d, %Y").date().isoformat() if date_match else ""
    labels = [
        ("Total equity", "股票基金"), ("Domestic", "美国股票基金"), ("World", "全球股票基金"),
        ("Hybrid", "混合基金"), ("Total bond", "债券基金"), ("Taxable", "应税债券基金"),
        ("Municipal", "市政债基金"), ("Total", "长期共同基金合计"),
    ]
    output = []
    for source_label, display_label in labels:
        match = re.search(rf"(?:^|\|)\s*{re.escape(source_label)}\s*\|\s*([-0-9,]+)", text, re.IGNORECASE)
        if not match:
            continue
        output.append({
            "category": display_label,
            "value_usd": float(match.group(1).replace(",", "")) * 1_000_000,
            "as_of": as_of,
            "frequency": "周频",
            "scope": "美国长期共同基金，不含ETF",
            "source": "ICI公开周报",
            "url": url,
        })
    if len(output) < 5:
        raise ValueError("insufficient ICI weekly flow data")
    return output


def fetch_tic_cross_border_flows() -> list[dict[str, Any]]:
    url = "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_table1.txt"
    text = get_text(url, timeout=50)
    row = next((line.split("\t") for line in text.splitlines() if line.startswith("Grand Total\t99996\t")), None)
    if not row or len(row) < 17:
        raise ValueError("missing TIC grand total")
    categories = [
        (4, "美国长期证券合计"), (7, "美国国债"), (10, "美国机构债"),
        (13, "美国公司债"), (16, "美国股票"),
    ]
    output = []
    for index, category in categories:
        value = as_float(row[index])
        if value is None:
            continue
        output.append({
            "category": category,
            "value_usd": value * 1_000_000,
            "as_of": row[2],
            "frequency": "月频",
            "scope": "外国投资者对美国长期证券净买入",
            "source": "美国财政部TIC",
            "url": "https://home.treasury.gov/data/treasury-international-capital-tic-system",
        })
    if len(output) < 4:
        raise ValueError("insufficient TIC flow data")
    return output


AI_MODEL_PRICING = [
    {"provider": "OpenAI", "model": "GPT-5.6 Sol", "context": "Standard·短上下文", "input_per_m": "$5", "cached_input_per_m": "$0.50", "output_per_m": "$30", "focus": "旗舰推理、Agent与复杂研究", "url": "https://platform.openai.com/pricing"},
    {"provider": "OpenAI", "model": "GPT-5.6 Terra", "context": "Standard·短上下文", "input_per_m": "$2.50", "cached_input_per_m": "$0.25", "output_per_m": "$15", "focus": "通用知识工作与投研自动化", "url": "https://platform.openai.com/pricing"},
    {"provider": "OpenAI", "model": "GPT-5.6 Luna", "context": "Standard·短上下文", "input_per_m": "$1", "cached_input_per_m": "$0.10", "output_per_m": "$6", "focus": "高频摘要、分类与批量处理", "url": "https://platform.openai.com/pricing"},
    {"provider": "Anthropic", "model": "Claude Fable 5", "context": "1M", "input_per_m": "$10", "cached_input_per_m": "$1", "output_per_m": "$50", "focus": "高难度研究与长文档", "url": "https://platform.claude.com/docs/en/about-claude/pricing"},
    {"provider": "Anthropic", "model": "Claude Opus 5", "context": "1M", "input_per_m": "$5", "cached_input_per_m": "$0.50", "output_per_m": "$25", "focus": "复杂推理、多Agent与专业研究", "url": "https://platform.claude.com/docs/en/about-claude/pricing"},
    {"provider": "Anthropic", "model": "Claude Sonnet 5", "context": "1M", "input_per_m": "$2", "cached_input_per_m": "$0.20", "output_per_m": "$10", "focus": "代码、知识工作与长上下文", "url": "https://platform.claude.com/docs/en/about-claude/pricing"},
    {"provider": "Anthropic", "model": "Claude Haiku 4.5", "context": "200K", "input_per_m": "$1", "cached_input_per_m": "$0.10", "output_per_m": "$5", "focus": "低延迟与高吞吐任务", "url": "https://platform.claude.com/docs/en/about-claude/pricing"},
    {"provider": "Google", "model": "Gemini 3.7 Flash", "context": "促销价至2026-12-31", "input_per_m": "$0.75", "cached_input_per_m": "$0.075", "output_per_m": "$3.75", "focus": "多模态、Agent与代码", "url": "https://ai.google.dev/gemini-api/docs/pricing"},
    {"provider": "Google", "model": "Gemini 3.5 Flash", "context": "标准", "input_per_m": "$1.50", "cached_input_per_m": "$0.15", "output_per_m": "$9", "focus": "高质量快速推理与搜索增强", "url": "https://ai.google.dev/gemini-api/docs/pricing"},
    {"provider": "Google", "model": "Gemini 3.1 Flash-Lite", "context": "标准·文本/图像/视频", "input_per_m": "$0.25", "cached_input_per_m": "$0.025", "output_per_m": "$1.50", "focus": "翻译、数据处理与大规模调用", "url": "https://ai.google.dev/gemini-api/docs/pricing"},
    {"provider": "xAI", "model": "Grok 4.6", "context": "500K·低于200K提示", "input_per_m": "$2", "cached_input_per_m": "$0.50", "output_per_m": "$6", "focus": "实时信息、代码与Agent", "url": "https://docs.x.ai/developers/grok-4-6"},
    {"provider": "xAI", "model": "Grok 4.3", "context": "1M", "input_per_m": "$1.25", "cached_input_per_m": "$0.20", "output_per_m": "$2.50", "focus": "工具调用与通用推理", "url": "https://docs.x.ai/developers/models/grok-4.3"},
    {"provider": "Mistral", "model": "Mistral Large 3", "context": "标准", "input_per_m": "$0.50", "cached_input_per_m": "$0.05", "output_per_m": "$1.50", "focus": "旗舰多语言与企业任务", "url": "https://docs.mistral.ai/inference/pricing"},
    {"provider": "Mistral", "model": "Mistral Medium 3.5", "context": "标准", "input_per_m": "$1.50", "cached_input_per_m": "$0.15", "output_per_m": "$7.50", "focus": "多模态、代码与Agent", "url": "https://docs.mistral.ai/inference/pricing"},
    {"provider": "Mistral", "model": "Mistral Small 4", "context": "标准", "input_per_m": "$0.15", "cached_input_per_m": "$0.015", "output_per_m": "$0.60", "focus": "低成本生产任务", "url": "https://docs.mistral.ai/inference/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek V4 Flash", "context": "1M·工作日峰值", "input_per_m": "$0.44", "cached_input_per_m": "$0.014", "output_per_m": "$1.32", "focus": "高吞吐推理、代码与Agent", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek V4 Pro", "context": "1M·工作日峰值", "input_per_m": "$1.32", "cached_input_per_m": "$0.044", "output_per_m": "$3.96", "focus": "复杂推理、代码与专业研究", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek V4 Flash Vision Exp", "context": "1M·实验版·工作日峰值", "input_per_m": "$0.44", "cached_input_per_m": "$0.014", "output_per_m": "$1.32", "focus": "图文理解与多模态任务", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
]


PRICING_SOURCES = {
    "OpenAI": {
        "url": "https://platform.openai.com/pricing",
        "models": {
            "GPT-5.6 Sol": ("gpt-5.6-sol", (0, 1, 3)),
            "GPT-5.6 Terra": ("gpt-5.6-terra", (0, 1, 3)),
            "GPT-5.6 Luna": ("gpt-5.6-luna", (0, 1, 3)),
        },
    },
    "Anthropic": {
        "url": "https://platform.claude.com/docs/en/about-claude/pricing",
        "models": {
            "Claude Fable 5": ("Claude Fable 5", (0, 3, 4)),
            "Claude Opus 5": ("Claude Opus 5", (0, 3, 4)),
            "Claude Sonnet 5": ("Claude Sonnet 5", (0, 3, 4)),
            "Claude Haiku 4.5": ("Claude Haiku 4.5", (0, 3, 4)),
        },
    },
    "Google": {
        "url": "https://ai.google.dev/gemini-api/docs/pricing",
        "models": {
            "Gemini 3.7 Flash": ("Gemini 3.7 Flash", (0, 4, 2)),
            "Gemini 3.5 Flash": ("Gemini 3.5 Flash", (0, 2, 1)),
            "Gemini 3.1 Flash-Lite": ("Gemini 3.1 Flash-Lite", (0, 3, 2)),
        },
    },
    "xAI": {
        "url": "https://docs.x.ai/developers/grok-4-6",
        "models": {"Grok 4.6": ("Input price", (0, -1, 1))},
    },
    "Mistral": {
        "url": "https://docs.mistral.ai/inference/pricing",
        "models": {
            "Mistral Large 3": ("Mistral Large 3", (0, 1, 2)),
            "Mistral Medium 3.5": ("Mistral Medium 3.5", (0, 1, 2)),
            "Mistral Small 4": ("Mistral Small 4", (0, 1, 2)),
        },
    },
    "DeepSeek": {
        "url": "https://api-docs.deepseek.com/quick_start/pricing",
        "models": {
            "DeepSeek V4 Flash": ("PRICING", (9, 3, 15)),
            "DeepSeek V4 Pro": ("PRICING", (10, 4, 16)),
            "DeepSeek V4 Flash Vision Exp": ("PRICING", (11, 5, 17)),
        },
    },
}


def _format_usd(value: str) -> str:
    number = float(value)
    precision = 4 if number < 0.1 else 2
    return "$" + f"{number:.{precision}f}".rstrip("0").rstrip(".")


def _prices_after(text: str, marker: str, indices: tuple[int, int, int]) -> tuple[str, str | None, str] | None:
    positions = [match.start() for match in re.finditer(re.escape(marker), text, re.IGNORECASE)]
    required = max(index for index in indices if index >= 0)
    for position in positions:
        values = re.findall(r"\$\s*([0-9]+(?:\.[0-9]+)?)", text[position:position + 900])
        if len(values) <= required:
            continue
        input_price = _format_usd(values[indices[0]])
        cached_price = _format_usd(values[indices[1]]) if indices[1] >= 0 else None
        output_price = _format_usd(values[indices[2]])
        return input_price, cached_price, output_price
    return None


def fetch_ai_model_pricing(previous_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    previous_map = {(row.get("provider"), row.get("model")): row for row in previous_rows}
    rows = [dict(previous_map.get((row["provider"], row["model"]), row)) for row in AI_MODEL_PRICING]
    for index, baseline in enumerate(AI_MODEL_PRICING):
        if baseline["provider"] == "OpenAI":
            rows[index].update(baseline)
    by_key = {(row["provider"], row["model"]): row for row in rows}
    statuses = []

    for provider, config in PRICING_SOURCES.items():
        started = time.time()
        parsed = 0
        try:
            text = get_page_text(str(config["url"]))
            for model, (marker, indices) in config["models"].items():
                prices = _prices_after(text, marker, indices)
                if not prices:
                    continue
                row = by_key[(provider, model)]
                row["input_per_m"], cached, row["output_per_m"] = prices
                if cached is not None:
                    row["cached_input_per_m"] = cached
                row["price_status"] = "官方实时"
                row["verified_at"] = now_iso()
                parsed += 1
            if parsed == 0:
                raise ValueError("no model price parsed")
            statuses.append({"key": f"model_pricing_{provider.lower()}", "status": "online", "updated_at": now_iso(), "latency_ms": round((time.time() - started) * 1000), "message": f"parsed {parsed}"})
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
            for row in rows:
                if row["provider"] == provider:
                    row["price_status"] = "官方基准" if provider == "OpenAI" or os.environ.get("SKIP_PRICING_NETWORK") == "1" else "缓存"
                    if provider == "OpenAI":
                        row["verified_at"] = now_iso()
                    else:
                        row.setdefault("verified_at", "")
            statuses.append({"key": f"model_pricing_{provider.lower()}", "status": "baseline" if provider == "OpenAI" else "cached", "updated_at": now_iso(), "message": "官方基准价；官方页拒绝自动抓取" if provider == "OpenAI" else type(exc).__name__})
        time.sleep(0.2)

    for row in rows:
        row.setdefault("price_status", "官方基准")
        row.setdefault("verified_at", now_iso())
    return rows, statuses


def fallback_payload(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "fmp_quotes": previous.get("fmp_quotes", []),
        "ai_chain_quotes": previous.get("ai_chain_quotes", []),
        "ai_valuations": previous.get("ai_valuations", []),
        "valuation_generated_at": previous.get("valuation_generated_at", ""),
        "fred_macro": previous.get("fred_macro", []),
        "eia_energy": previous.get("eia_energy", []),
        "twelve_fx": previous.get("twelve_fx", []),
        "market_history": previous.get("market_history", []),
        "commodity_market": previous.get("commodity_market", []),
        "cftc_positions": previous.get("cftc_positions", []),
        "etf_fund_flows": previous.get("etf_fund_flows", []),
        "ici_weekly_flows": previous.get("ici_weekly_flows", []),
        "tic_cross_border_flows": previous.get("tic_cross_border_flows", []),
        "gdelt_news": previous.get("gdelt_news", []),
        "alpha_news": previous.get("alpha_news", []),
        "ai_model_pricing": previous.get("ai_model_pricing", AI_MODEL_PRICING),
        "ai_chain_metrics": previous.get("ai_chain_metrics", []),
        "event_calendar": previous.get("event_calendar", []),
        "score_backtest": previous.get("score_backtest", []),
    }


def write_payload(payload: dict[str, Any]) -> None:
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    JS_PATH.write_text(
        "window.__ASSET_DASHBOARD_DATA__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    previous = read_previous()
    payload = fallback_payload(previous)
    statuses = []

    if "--pricing-only" in sys.argv:
        pricing, pricing_statuses = fetch_ai_model_pricing(previous.get("ai_model_pricing", []))
        payload.update(previous)
        payload["ai_model_pricing"] = pricing
        payload["pricing_generated_at"] = now_iso()
        old_statuses = [item for item in previous.get("source_status", []) if not str(item.get("key", "")).startswith("model_pricing_")]
        payload["source_status"] = old_statuses + pricing_statuses
        write_payload(payload)
        print(f"updated model pricing: {len(pricing)} rows")
        return 0

    for key, fetcher, fallback in [
        ("fmp_quotes", fetch_fmp_quotes, payload["fmp_quotes"]),
        ("ai_chain_quotes", lambda: fetch_ai_chain_quotes(payload["fmp_quotes"]), payload["ai_chain_quotes"]),
        ("ai_valuations", lambda: fetch_ai_valuations(previous.get("ai_valuations", []), previous.get("valuation_generated_at", "")), payload["ai_valuations"]),
        ("fred_macro", fetch_fred_series, payload["fred_macro"]),
        ("eia_energy", fetch_eia_energy, payload["eia_energy"]),
        ("twelve_fx", fetch_twelve_fx, payload["twelve_fx"]),
        ("market_history", fetch_market_history, payload["market_history"]),
        ("commodity_market", lambda: fetch_commodity_market(previous.get("commodity_market", [])), payload["commodity_market"]),
        ("cftc_positions", fetch_cftc_positions, payload["cftc_positions"]),
        ("etf_fund_flows", lambda: fetch_etf_fund_flows(previous.get("etf_fund_flows", [])), payload["etf_fund_flows"]),
        ("ici_weekly_flows", fetch_ici_weekly_flows, payload["ici_weekly_flows"]),
        ("tic_cross_border_flows", fetch_tic_cross_border_flows, payload["tic_cross_border_flows"]),
        ("event_calendar", fetch_event_calendar, payload["event_calendar"]),
        ("gdelt_news", fetch_gdelt_news, payload["gdelt_news"]),
        ("alpha_news", fetch_alpha_news, payload["alpha_news"]),
    ]:
        data, status = safe_source(previous, key, fetcher, fallback)
        payload[key] = data
        statuses.append(status)
        time.sleep(0.25)

    valuation_map = {str(item.get("symbol")): item.get("pe") for item in payload["ai_valuations"]}
    for quote in payload["ai_chain_quotes"]:
        if valuation_map.get(str(quote.get("symbol"))) is not None:
            quote["pe"] = valuation_map[str(quote.get("symbol"))]
    if payload["ai_valuations"]:
        payload["valuation_generated_at"] = now_iso()
    payload["ai_chain_metrics"] = build_ai_chain_metrics(payload["ai_chain_quotes"] or payload["fmp_quotes"])
    payload["score_backtest"] = build_score_backtest(payload["market_history"])
    try:
        groups, summary_status = enrich_news_summaries([payload["alpha_news"], payload["gdelt_news"]])
        payload["alpha_news"], payload["gdelt_news"] = groups
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        summary_status = {"key": "news_summary_zh", "status": "cached", "updated_at": now_iso(), "message": type(exc).__name__}
    statuses.append(summary_status)

    pricing, pricing_statuses = fetch_ai_model_pricing(previous.get("ai_model_pricing", []))
    payload["ai_model_pricing"] = pricing
    payload["pricing_generated_at"] = now_iso()
    statuses.extend(pricing_statuses)
    payload["generated_at"] = now_iso()
    payload["refresh_policy"] = {
        "workflow_cron": "23 */4 * * *",
        "description": "GitHub Actions 每4小时尝试更新；低频宏观源即使失败也保留上一版缓存。",
    }
    payload["source_status"] = statuses

    write_payload(payload)
    print("wrote data/latest.json and data/latest.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

