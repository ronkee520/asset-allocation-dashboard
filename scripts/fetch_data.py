from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
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
        ("CPIAUCSL", "美国CPI", "通胀", "通胀压力、降息交易节奏"),
        ("UNRATE", "美国失业率", "就业", "经济周期与风险偏好"),
        ("BAMLH0A0HYM2", "美国高收益债利差", "信用", "信用风险偏好、权益下行保护"),
    ]
    output = []
    for series_id, name, category, driver in series:
        url = "https://api.stlouisfed.org/fred/series/observations?" + urlencode({
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 2,
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


AI_MODEL_PRICING = [
    {"provider": "OpenAI", "model": "GPT-5", "context": "官方价格页", "input_per_m": "$1.25", "cached_input_per_m": "$0.125", "output_per_m": "$10.00", "focus": "复杂推理、Agent、投研自动化", "url": "https://platform.openai.com/docs/pricing"},
    {"provider": "OpenAI", "model": "GPT-5 mini", "context": "官方价格页", "input_per_m": "$0.25", "cached_input_per_m": "$0.025", "output_per_m": "$2.00", "focus": "高频摘要、分类、数据整理", "url": "https://platform.openai.com/docs/pricing"},
    {"provider": "OpenAI", "model": "GPT-5 nano", "context": "官方价格页", "input_per_m": "$0.05", "cached_input_per_m": "$0.005", "output_per_m": "$0.40", "focus": "低成本批量处理", "url": "https://platform.openai.com/docs/pricing"},
    {"provider": "Anthropic", "model": "Claude Opus 4.1", "context": "官方价格页", "input_per_m": "$15.00", "cached_input_per_m": "$1.50", "output_per_m": "$75.00", "focus": "高阶研究、复杂推理、代码审阅", "url": "https://www.anthropic.com/pricing"},
    {"provider": "Anthropic", "model": "Claude Sonnet 4", "context": "官方价格页", "input_per_m": "$3.00", "cached_input_per_m": "$0.30", "output_per_m": "$15.00", "focus": "企业知识工作、代码、长文档", "url": "https://www.anthropic.com/pricing"},
    {"provider": "Anthropic", "model": "Claude Haiku 3.5", "context": "官方价格页", "input_per_m": "$0.80", "cached_input_per_m": "$0.08", "output_per_m": "$4.00", "focus": "低延迟、批量任务", "url": "https://www.anthropic.com/pricing"},
    {"provider": "Google", "model": "Gemini 2.5 Pro", "context": "<=200K tokens", "input_per_m": "$1.25", "cached_input_per_m": "$0.31", "output_per_m": "$10.00", "focus": "多模态、长上下文、复杂推理", "url": "https://ai.google.dev/gemini-api/docs/pricing"},
    {"provider": "Google", "model": "Gemini 2.5 Flash", "context": "官方价格页", "input_per_m": "$0.30", "cached_input_per_m": "$0.075", "output_per_m": "$2.50", "focus": "高吞吐、多模态、低成本推理", "url": "https://ai.google.dev/gemini-api/docs/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek Chat", "context": "官方价格页", "input_per_m": "$0.27", "cached_input_per_m": "$0.07", "output_per_m": "$1.10", "focus": "中文、代码、低成本推理", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
    {"provider": "DeepSeek", "model": "DeepSeek Reasoner", "context": "官方价格页", "input_per_m": "$0.55", "cached_input_per_m": "$0.14", "output_per_m": "$2.19", "focus": "推理、数学、代码任务", "url": "https://api-docs.deepseek.com/quick_start/pricing"},
    {"provider": "xAI", "model": "Grok 4", "context": "官方价格页", "input_per_m": "$3.00", "cached_input_per_m": "$0.75", "output_per_m": "$15.00", "focus": "实时信息、X生态、图文输入", "url": "https://docs.x.ai/docs/models"},
    {"provider": "Mistral", "model": "Mistral Large", "context": "官方价格页", "input_per_m": "$2.00", "cached_input_per_m": "-", "output_per_m": "$6.00", "focus": "欧洲AI、多语言、企业部署", "url": "https://mistral.ai/pricing/api/"},
]


def fallback_payload(previous: dict[str, Any]) -> dict[str, Any]:
    return {
        "fmp_quotes": previous.get("fmp_quotes", []),
        "fred_macro": previous.get("fred_macro", []),
        "eia_energy": previous.get("eia_energy", []),
        "twelve_fx": previous.get("twelve_fx", []),
        "gdelt_news": previous.get("gdelt_news", []),
        "alpha_news": previous.get("alpha_news", []),
        "ai_model_pricing": AI_MODEL_PRICING,
    }


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    previous = read_previous()
    payload = fallback_payload(previous)
    statuses = []

    for key, fetcher, fallback in [
        ("fmp_quotes", fetch_fmp_quotes, payload["fmp_quotes"]),
        ("fred_macro", fetch_fred_series, payload["fred_macro"]),
        ("eia_energy", fetch_eia_energy, payload["eia_energy"]),
        ("twelve_fx", fetch_twelve_fx, payload["twelve_fx"]),
        ("gdelt_news", fetch_gdelt_news, payload["gdelt_news"]),
        ("alpha_news", fetch_alpha_news, payload["alpha_news"]),
    ]:
        data, status = safe_source(previous, key, fetcher, fallback)
        payload[key] = data
        statuses.append(status)
        time.sleep(0.25)

    payload["ai_model_pricing"] = AI_MODEL_PRICING
    payload["generated_at"] = now_iso()
    payload["refresh_policy"] = {
        "workflow_cron": "23 */4 * * *",
        "description": "GitHub Actions 每4小时尝试更新；低频宏观源即使失败也保留上一版缓存。",
    }
    payload["source_status"] = statuses

    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    JS_PATH.write_text(
        "window.__ASSET_DASHBOARD_DATA__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print("wrote data/latest.json and data/latest.js")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
