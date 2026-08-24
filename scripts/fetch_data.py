from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
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
    time.sleep(6)
    query = "(AI OR semiconductor OR Nvidia OR oil OR gold OR central bank OR ETF OR inflation OR copper) market"
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode({
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 12,
        "sort": "hybridrel",
    })
    payload = get_json(url)
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


ETF_FUND_SOURCES = [
    {
        "symbol": "SPY",
        "asset": "美股",
        "issuer": "State Street",
        "parser": "ssga",
        "url": "https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy",
    },
    {
        "symbol": "GLD",
        "asset": "黄金",
        "issuer": "State Street",
        "parser": "ssga",
        "url": "https://www.ssga.com/us/en/individual/etfs/spdr-gold-shares-gld",
    },
    {
        "symbol": "TLT",
        "asset": "美债",
        "issuer": "iShares",
        "parser": "ishares",
        "url": "https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf",
    },
    {
        "symbol": "EWH",
        "asset": "港股",
        "issuer": "iShares",
        "parser": "ishares",
        "url": "https://www.ishares.com/us/products/239657/ishares-msci-hong-kong-etf",
    },
    {
        "symbol": "BOTZ",
        "asset": "AI",
        "issuer": "Global X",
        "parser": "globalx",
        "url": "https://www.globalxetfs.com/funds/botz",
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

        output.append({
            "symbol": source["symbol"],
            "asset": source["asset"],
            "issuer": source["issuer"],
            "as_of": current["as_of"],
            "nav": current["nav"],
            "shares_outstanding": current["shares_outstanding"],
            "shares_change": shares_change,
            "shares_change_pct": shares_change_pct,
            "estimated_flow": estimated_flow,
            "method": "发行商流通份额变化 × 当日NAV",
            "source": "基金发行商官网",
            "data_status": "online",
            "url": source["url"],
            "history": history,
        })
        time.sleep(0.35)
    if len(output) < 3:
        raise ValueError("insufficient official ETF fund data")
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
    {"provider": "DeepSeek", "model": "DeepSeek Chat", "context": "官方标准价", "input_per_m": "$0.27", "cached_input_per_m": "$0.07", "output_per_m": "$1.10", "focus": "中文、代码与低成本推理", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek Reasoner", "context": "官方标准价", "input_per_m": "$0.55", "cached_input_per_m": "$0.14", "output_per_m": "$2.19", "focus": "数学、代码与深度推理", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
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
            "DeepSeek Chat": ("deepseek-chat", (0, 1, 2)),
            "DeepSeek Reasoner": ("deepseek-reasoner", (0, 1, 2)),
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
            statuses.append({"key": f"model_pricing_{provider.lower()}", "status": "cached", "updated_at": now_iso(), "message": type(exc).__name__})
        time.sleep(0.2)

    for row in rows:
        row.setdefault("price_status", "官方基准")
        row.setdefault("verified_at", now_iso())
    return rows, statuses


def fallback_payload(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "fmp_quotes": previous.get("fmp_quotes", []),
        "fred_macro": previous.get("fred_macro", []),
        "eia_energy": previous.get("eia_energy", []),
        "twelve_fx": previous.get("twelve_fx", []),
        "market_history": previous.get("market_history", []),
        "etf_fund_flows": previous.get("etf_fund_flows", []),
        "gdelt_news": previous.get("gdelt_news", []),
        "alpha_news": previous.get("alpha_news", []),
        "ai_model_pricing": previous.get("ai_model_pricing", AI_MODEL_PRICING),
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
        ("fred_macro", fetch_fred_series, payload["fred_macro"]),
        ("eia_energy", fetch_eia_energy, payload["eia_energy"]),
        ("twelve_fx", fetch_twelve_fx, payload["twelve_fx"]),
        ("market_history", fetch_market_history, payload["market_history"]),
        ("etf_fund_flows", lambda: fetch_etf_fund_flows(previous.get("etf_fund_flows", [])), payload["etf_fund_flows"]),
        ("gdelt_news", fetch_gdelt_news, payload["gdelt_news"]),
        ("alpha_news", fetch_alpha_news, payload["alpha_news"]),
    ]:
        data, status = safe_source(previous, key, fetcher, fallback)
        payload[key] = data
        statuses.append(status)
        time.sleep(0.25)

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
