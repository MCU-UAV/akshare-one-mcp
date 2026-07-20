from datetime import date, datetime, time, timedelta, timezone
import json
import math
import re
from typing import Annotated, Any, Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastmcp import FastMCP
from pydantic import Field


mcp = FastMCP(name="akshare-one-mcp")

CN_TZ = timezone(timedelta(hours=8))
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0"}

SINA_REALTIME_URL = "https://hq.sinajs.cn/list={symbols}"
SINA_MARKET_COUNT_URL = (
    "http://vip.stock.finance.sina.com.cn/quotes_service/api/"
    "json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a"
)
SINA_MARKET_PAGE_URL = (
    "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData"
)
TENCENT_REALTIME_URL = "https://qt.gtimg.cn/q={symbols}"
TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/kline/kline"
TENCENT_FQ_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
EASTMONEY_NEWS_URL = "https://search-api-web.eastmoney.com/search/jsonp"
EASTMONEY_ANNOUNCEMENT_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
EASTMONEY_MONEY_FLOW_URLS = [
    "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get",
    "https://82.push2.eastmoney.com/api/qt/stock/fflow/daykline/get",
    "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
    "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get",
    "https://82.push2.eastmoney.com/api/qt/stock/fflow/kline/get",
]
SINA_FINANCE_REPORT_URL = (
    "https://quotes.sina.cn/cn/api/openapi.php/"
    "CompanyFinanceService.getFinanceReport2022"
)
XUEQIU_INSIDER_URL = "https://xueqiu.com/service/v5/stock/f10/cn/skholderchg"

Record = dict[str, Any]

INDEX_SYMBOLS = {
    "sh000001": "sh000001",
    "000001": "sh000001",
    "shanghai": "sh000001",
    "sse": "sh000001",
    "上证指数": "sh000001",
    "sz399001": "sz399001",
    "399001": "sz399001",
    "shenzhen": "sz399001",
    "szse": "sz399001",
    "深证成指": "sz399001",
    "sz399006": "sz399006",
    "399006": "sz399006",
    "chinext": "sz399006",
    "创业板指": "sz399006",
    "sh000300": "sh000300",
    "000300": "sh000300",
    "csi300": "sh000300",
    "沪深300": "sh000300",
    "sh000905": "sh000905",
    "000905": "sh000905",
    "csi500": "sh000905",
    "中证500": "sh000905",
    "sh000852": "sh000852",
    "000852": "sh000852",
    "csi1000": "sh000852",
    "中证1000": "sh000852",
}


def _json_records(records: list[Record]) -> str:
    return json.dumps(records, ensure_ascii=False, separators=(",", ":"))


def _http_get_text(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    encoding: str = "utf-8",
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> str:
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(url, headers={**HTTP_HEADERS, **(headers or {})})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode(encoding, errors="replace")


def _http_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> Any:
    return json.loads(_http_get_text(url, params, headers=headers, timeout=timeout))


def _to_float(value: Any) -> float | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _strip_exchange_prefix(symbol: str) -> str:
    lower = symbol.lower()
    if lower.startswith(("sh", "sz", "bj")):
        return symbol[2:]
    return symbol


def _with_exchange_prefix(symbol: str) -> str:
    symbol = symbol.lower()
    if symbol.startswith(("sh", "sz", "bj")):
        return symbol

    code = _strip_exchange_prefix(symbol)
    if code.startswith(("600", "601", "603", "605", "688", "689", "900", "5", "6", "9")):
        return f"sh{code}"
    if code.startswith(("43", "83", "87", "88", "92")):
        return f"bj{code}"
    return f"sz{code}"


def _normalize_index_symbol(symbol: str) -> str:
    key = symbol.strip().lower()
    return INDEX_SYMBOLS.get(key, _with_exchange_prefix(symbol))


def _eastmoney_secid(symbol: str) -> str:
    stock = _with_exchange_prefix(symbol)
    if stock.startswith("sh"):
        return f"1.{stock[2:]}"
    if stock.startswith("bj"):
        return f"0.{stock[2:]}"
    return f"0.{stock[2:]}"


def _market_code_for_sina(symbol: str) -> str:
    lower = symbol.lower()
    if lower.startswith(("sh", "sz", "bj")):
        return lower
    return _with_exchange_prefix(symbol)


def _iso_from_date(date_text: str) -> str:
    return datetime.combine(date.fromisoformat(date_text), time(), tzinfo=CN_TZ).isoformat()


def _iso_from_compact_date(date_text: str) -> str:
    parsed = datetime.strptime(date_text, "%Y%m%d").replace(tzinfo=CN_TZ)
    return parsed.isoformat()


def _parse_sina_realtime_line(symbol: str, line: str) -> Record:
    _, _, quoted = line.partition('="')
    payload = quoted.rsplit('";', 1)[0]
    fields = payload.split(",") if payload else []
    if len(fields) < 32 or not fields[0]:
        raise ValueError(f"Empty realtime data returned from Sina for {symbol}")

    prev_close = _to_float(fields[2]) or 0.0
    price = _to_float(fields[3]) or 0.0
    change = price - prev_close
    timestamp = datetime.fromisoformat(f"{fields[30]}T{fields[31]}").replace(tzinfo=CN_TZ)
    return {
        "symbol": _strip_exchange_prefix(symbol),
        "price": price,
        "change": change,
        "pct_change": (change / prev_close * 100) if prev_close else 0.0,
        "timestamp": timestamp.isoformat(),
        "volume": _to_float(fields[8]),
        "amount": _to_float(fields[9]),
        "open": _to_float(fields[1]),
        "high": _to_float(fields[4]),
        "low": _to_float(fields[5]),
        "prev_close": prev_close,
    }


def _get_sina_market_realtime_data() -> list[Record]:
    count_text = _http_get_text(SINA_MARKET_COUNT_URL)
    count_match = re.search(r"\d+", count_text)
    if not count_match:
        raise ValueError("Failed to read Sina market stock count")

    page_count = math.ceil(int(count_match.group()) / 80)
    records: list[Record] = []
    for page in range(1, page_count + 1):
        data = _http_get_json(
            SINA_MARKET_PAGE_URL,
            {
                "page": page,
                "num": 80,
                "sort": "symbol",
                "asc": 1,
                "node": "hs_a",
                "symbol": "",
                "_s_r_a": "page",
            },
            timeout=12,
        )
        for item in data:
            prev_close = _to_float(item.get("settlement")) or 0.0
            price = _to_float(item.get("trade")) or 0.0
            records.append(
                {
                    "symbol": _strip_exchange_prefix(str(item.get("symbol", ""))),
                    "price": price,
                    "change": _to_float(item.get("pricechange")),
                    "pct_change": _to_float(item.get("changepercent")),
                    "timestamp": datetime.now(CN_TZ).isoformat(),
                    "volume": _to_float(item.get("volume")),
                    "amount": _to_float(item.get("amount")),
                    "open": _to_float(item.get("open")),
                    "high": _to_float(item.get("high")),
                    "low": _to_float(item.get("low")),
                    "prev_close": prev_close,
                }
            )
    return records


def _get_sina_realtime_data(symbol: str | None) -> list[Record]:
    if symbol is None:
        return _get_sina_market_realtime_data()

    sina_symbol = _market_code_for_sina(symbol)
    text = _http_get_text(
        SINA_REALTIME_URL.format(symbols=sina_symbol),
        encoding="GB18030",
        headers={"Referer": "https://finance.sina.com.cn/"},
    )
    return [_parse_sina_realtime_line(symbol, text)]


def _get_tencent_realtime_data(symbol: str | None) -> list[Record]:
    if symbol is None:
        return _get_sina_market_realtime_data()

    tencent_symbol = _with_exchange_prefix(symbol)
    text = _http_get_text(
        TENCENT_REALTIME_URL.format(symbols=tencent_symbol),
        encoding="GBK",
        headers={"Referer": "https://gu.qq.com/"},
    )
    _, _, quoted = text.partition('="')
    payload = quoted.rsplit('";', 1)[0]
    fields = payload.split("~") if payload else []
    if len(fields) < 49 or not fields[1]:
        raise ValueError(f"Empty realtime data returned from Tencent for {symbol}")

    timestamp = datetime.strptime(fields[30], "%Y%m%d%H%M%S").replace(tzinfo=CN_TZ)
    return [
        {
            "symbol": _strip_exchange_prefix(symbol),
            "price": _to_float(fields[3]),
            "change": _to_float(fields[31]),
            "pct_change": _to_float(fields[32]),
            "timestamp": timestamp.isoformat(),
            "volume": (_to_float(fields[36]) or 0.0) * 100,
            "amount": (_to_float(fields[37]) or 0.0) * 10000,
            "open": _to_float(fields[5]),
            "high": _to_float(fields[33]),
            "low": _to_float(fields[34]),
            "prev_close": _to_float(fields[4]),
        }
    ]


def _fetch_tencent_quote(symbol: str) -> list[str]:
    text = _http_get_text(
        TENCENT_REALTIME_URL.format(symbols=symbol),
        encoding="GBK",
        headers={"Referer": "https://gu.qq.com/"},
    )
    _, _, quoted = text.partition('="')
    payload = quoted.rsplit('";', 1)[0]
    fields = payload.split("~") if payload else []
    if len(fields) < 49 or not fields[1]:
        raise ValueError(f"Empty quote data returned from Tencent for {symbol}")
    return fields


def _quote_timestamp(value: str) -> str | None:
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=CN_TZ).isoformat()
    except ValueError:
        return None


def _get_stock_snapshot_record(symbol: str) -> Record:
    stock = _with_exchange_prefix(symbol)
    fields = _fetch_tencent_quote(stock)
    return {
        "symbol": _strip_exchange_prefix(symbol),
        "name": fields[1],
        "price": _to_float(fields[3]),
        "prev_close": _to_float(fields[4]),
        "open": _to_float(fields[5]),
        "change": _to_float(fields[31]),
        "pct_change": _to_float(fields[32]),
        "high": _to_float(fields[33]),
        "low": _to_float(fields[34]),
        "volume": (_to_float(fields[36]) or 0.0) * 100,
        "amount": (_to_float(fields[37]) or 0.0) * 10000,
        "turnover_rate": _to_float(fields[38]),
        "pe_ttm": _to_float(fields[39]),
        "amplitude": _to_float(fields[43]),
        "market_cap": (_to_float(fields[45]) or 0.0) * 100000000,
        "float_market_cap": (_to_float(fields[44]) or 0.0) * 100000000,
        "pb": _to_float(fields[46]),
        "limit_up": _to_float(fields[47]),
        "limit_down": _to_float(fields[48]),
        "timestamp": _quote_timestamp(fields[30]),
        "bid_levels": [
            {"price": _to_float(fields[index]), "volume": (_to_float(fields[index + 1]) or 0.0) * 100}
            for index in (9, 11, 13, 15, 17)
        ],
        "ask_levels": [
            {"price": _to_float(fields[index]), "volume": (_to_float(fields[index + 1]) or 0.0) * 100}
            for index in (19, 21, 23, 25, 27)
        ],
    }


def _get_index_records(symbols: list[str]) -> list[Record]:
    records: list[Record] = []
    for symbol in symbols:
        stock = _normalize_index_symbol(symbol)
        fields = _fetch_tencent_quote(stock)
        records.append(
            {
                "symbol": stock,
                "name": fields[1],
                "price": _to_float(fields[3]),
                "prev_close": _to_float(fields[4]),
                "open": _to_float(fields[5]),
                "change": _to_float(fields[31]),
                "pct_change": _to_float(fields[32]),
                "high": _to_float(fields[33]),
                "low": _to_float(fields[34]),
                "volume": _to_float(fields[36]),
                "amount": (_to_float(fields[37]) or 0.0) * 10000,
                "turnover_rate": _to_float(fields[38]),
                "amplitude": _to_float(fields[43]),
                "timestamp": _quote_timestamp(fields[30]),
            }
        )
    return records


def _get_realtime_data(symbol: str | None, source: str) -> list[Record]:
    if source == "tencent":
        return _get_tencent_realtime_data(symbol)
    try:
        return _get_sina_realtime_data(symbol)
    except Exception:
        return _get_tencent_realtime_data(symbol)


def _tencent_kline_period(interval: str, interval_multiplier: int) -> str:
    if interval == "minute":
        return f"m{interval_multiplier if interval_multiplier in (1, 5, 15, 30) else 1}"
    if interval == "hour":
        return "m60"
    if interval in ("week", "month"):
        return interval
    return "day"


def _get_hist_data(
    symbol: str,
    interval: str,
    interval_multiplier: int,
    start_date: str,
    end_date: str,
    adjust: str,
) -> list[Record]:
    stock = _with_exchange_prefix(symbol)
    period = _tencent_kline_period(interval, interval_multiplier)
    adjusted = adjust in ("qfq", "hfq")
    endpoint = TENCENT_FQ_KLINE_URL if adjusted else TENCENT_KLINE_URL
    key = f"{adjust}{period}" if adjusted else period
    data = _http_get_json(
        endpoint,
        {"param": f"{stock},{period},{start_date},{end_date},640,{adjust}" if adjusted else f"{stock},{period},{start_date},{end_date},640"},
        headers={"Referer": "https://gu.qq.com/"},
    )
    stock_data = data.get("data", {}).get(stock, {})
    rows = stock_data.get(key) or stock_data.get(period) or []
    records = [
        {
            "timestamp": _iso_from_date(row[0].split(" ")[0]),
            "open": _to_float(row[1]),
            "high": _to_float(row[3]),
            "low": _to_float(row[4]),
            "close": _to_float(row[2]),
            "volume": (_to_float(row[5]) or 0.0) * 100,
        }
        for row in rows
        if len(row) >= 6
    ]
    if interval == "year":
        records = _resample_by_year(records)
    elif interval == "day" and interval_multiplier > 1:
        records = _resample_by_chunk(records, interval_multiplier)
    return records


def _resample_by_chunk(records: list[Record], size: int) -> list[Record]:
    grouped = [records[i : i + size] for i in range(0, len(records), size)]
    return [_merge_ohlcv(group) for group in grouped if group]


def _resample_by_year(records: list[Record]) -> list[Record]:
    groups: dict[str, list[Record]] = {}
    for record in records:
        groups.setdefault(str(record["timestamp"])[:4], []).append(record)
    return [_merge_ohlcv(groups[key]) for key in sorted(groups)]


def _merge_ohlcv(records: list[Record]) -> Record:
    return {
        "timestamp": records[0]["timestamp"],
        "open": records[0]["open"],
        "high": max((r["high"] for r in records if r["high"] is not None), default=None),
        "low": min((r["low"] for r in records if r["low"] is not None), default=None),
        "close": records[-1]["close"],
        "volume": sum((r["volume"] or 0.0) for r in records),
    }


def _add_indicators(records: list[Record], indicators_list: list[str]) -> None:
    closes = [r.get("close") for r in records]
    if "SMA" in indicators_list:
        for record, value in zip(records, _sma(closes, 20), strict=True):
            record["sma"] = value
    if "EMA" in indicators_list:
        for record, value in zip(records, _ema(closes, 20), strict=True):
            record["ema"] = value
    if "RSI" in indicators_list:
        for record, value in zip(records, _rsi(closes, 14), strict=True):
            record["rsi"] = value
    if "MACD" in indicators_list:
        macd, signal, histogram = _macd(closes)
        for index, record in enumerate(records):
            record["macd"] = macd[index]
            record["signal"] = signal[index]
            record["histogram"] = histogram[index]
    if "BOLL" in indicators_list:
        upper, middle, lower = _boll(closes, 20, 2)
        for index, record in enumerate(records):
            record["boll_upper"] = upper[index]
            record["boll_middle"] = middle[index]
            record["boll_lower"] = lower[index]


def _sma(values: list[Any], window: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        sample = [_to_float(v) for v in values[max(0, index - window + 1) : index + 1]]
        clean = [v for v in sample if v is not None]
        result.append(sum(clean) / len(clean) if len(clean) == window else None)
    return result


def _ema(values: list[Any], window: int) -> list[float | None]:
    alpha = 2 / (window + 1)
    result: list[float | None] = []
    previous: float | None = None
    for raw in values:
        value = _to_float(raw)
        if value is None:
            result.append(previous)
            continue
        previous = value if previous is None else value * alpha + previous * (1 - alpha)
        result.append(previous)
    return result


def _rsi(values: list[Any], window: int) -> list[float | None]:
    result: list[float | None] = [None]
    gains: list[float] = []
    losses: list[float] = []
    for prev, current in zip(values, values[1:], strict=False):
        prev_value = _to_float(prev)
        current_value = _to_float(current)
        change = 0.0 if prev_value is None or current_value is None else current_value - prev_value
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
        if len(gains) < window:
            result.append(None)
            continue
        avg_gain = sum(gains[-window:]) / window
        avg_loss = sum(losses[-window:]) / window
        result.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + avg_gain / avg_loss)))
    return result


def _macd(values: list[Any]) -> tuple[list[float | None], list[float | None], list[float | None]]:
    ema_fast = _ema(values, 12)
    ema_slow = _ema(values, 26)
    macd = [
        (fast - slow) if fast is not None and slow is not None else None
        for fast, slow in zip(ema_fast, ema_slow, strict=True)
    ]
    signal = _ema(macd, 9)
    histogram = [
        (m - s) if m is not None and s is not None else None
        for m, s in zip(macd, signal, strict=True)
    ]
    return macd, signal, histogram


def _boll(values: list[Any], window: int, std: float) -> tuple[list[float | None], list[float | None], list[float | None]]:
    upper: list[float | None] = []
    middle: list[float | None] = []
    lower: list[float | None] = []
    for index in range(len(values)):
        sample = [_to_float(v) for v in values[max(0, index - window + 1) : index + 1]]
        clean = [v for v in sample if v is not None]
        if len(clean) != window:
            upper.append(None)
            middle.append(None)
            lower.append(None)
            continue
        mean = sum(clean) / window
        variance = sum((value - mean) ** 2 for value in clean) / window
        width = math.sqrt(variance) * std
        upper.append(mean + width)
        middle.append(mean)
        lower.append(mean - width)

    return upper, middle, lower


def _get_news_records(symbol: str) -> list[Record]:
    callback = "jQuery35101792940631092459_1764599530165"
    inner_param = {
        "uid": "",
        "keyword": symbol,
        "type": ["cmsArticleWebOld"],
        "client": "web",
        "clientType": "web",
        "clientVersion": "curr",
        "param": {
            "cmsArticleWebOld": {
                "searchScope": "default",
                "sort": "default",
                "pageIndex": 1,
                "pageSize": 20,
                "preTag": "<em>",
                "postTag": "</em>",
            }
        },
    }
    text = _http_get_text(
        EASTMONEY_NEWS_URL,
        {"cb": callback, "param": json.dumps(inner_param, ensure_ascii=False), "_": "1764599530176"},
        headers={"Referer": f"https://so.eastmoney.com/news/s?keyword={symbol}"},
    )
    prefix = f"{callback}("
    if text.startswith(prefix):
        text = text[len(prefix) : -1]
    payload = json.loads(text)
    records = []
    tag_re = re.compile(r"</?em>|\(<em>|</em>\)")
    for item in payload.get("result", {}).get("cmsArticleWebOld", []):
        title = tag_re.sub("", item.get("title") or "")
        content = tag_re.sub("", item.get("content") or "").replace("\u3000", "").replace("\r\n", " ")
        records.append(
            {
                "keyword": symbol,
                "title": title,
                "content": content,
                "publish_time": item.get("date"),
                "source": item.get("mediaName"),
                "url": f"http://finance.eastmoney.com/a/{item.get('code')}.html",
            }
        )
    return records


ANNOUNCEMENT_CATEGORY_MAP = {
    "all": "0",
    "financial_report": "1",
    "financing": "2",
    "risk": "3",
    "info_change": "4",
    "major_event": "5",
    "restructuring": "6",
    "shareholding_change": "7",
}


def _clean_eastmoney_jsonp(text: str, callback: str) -> Any:
    prefix = f"{callback}("
    if text.startswith(prefix) and text.endswith(")"):
        text = text[len(prefix) : -1]
    return json.loads(text)


def _get_announcement_records(
    symbol: str,
    category: str,
    recent_n: int | None,
) -> list[Record]:
    page_size = recent_n if recent_n is not None else 20
    page_size = max(1, min(page_size, 100))
    callback = "cb"
    params = {
        "cb": callback,
        "sr": "-1",
        "page_size": str(page_size),
        "page_index": "1",
        "ann_type": "A",
        "client_source": "web",
        "stock_list": _strip_exchange_prefix(symbol),
    }
    if category != "all":
        params["f_node"] = ANNOUNCEMENT_CATEGORY_MAP[category]
        params["s_node"] = "0"

    text = _http_get_text(
        EASTMONEY_ANNOUNCEMENT_URL,
        params,
        headers={"Referer": "https://data.eastmoney.com/notices/"},
    )
    payload = _clean_eastmoney_jsonp(text, callback)
    records = []
    for item in payload.get("data", {}).get("list", []) or []:
        codes = item.get("codes") or []
        code_info = next(
            (code for code in codes if str(code.get("stock_code")) == _strip_exchange_prefix(symbol)),
            codes[0] if codes else {},
        )
        columns = item.get("columns") or []
        column_info = columns[0] if columns else {}
        stock_code = code_info.get("stock_code") or _strip_exchange_prefix(symbol)
        art_code = item.get("art_code")
        records.append(
            {
                "symbol": stock_code,
                "name": code_info.get("short_name"),
                "title": item.get("title_ch") or item.get("title"),
                "category": column_info.get("column_name"),
                "category_code": column_info.get("column_code"),
                "publish_time": item.get("display_time"),
                "notice_date": item.get("notice_date"),
                "art_code": art_code,
                "url": (
                    f"https://data.eastmoney.com/notices/detail/{stock_code}/{art_code}.html"
                    if stock_code and art_code
                    else None
                ),
            }
        )
    return records


def _get_money_flow_records(symbol: str) -> list[Record]:
    params = {
        "lmt": "0",
        "klt": "101",
        "secid": _eastmoney_secid(symbol),
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
    }
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://data.eastmoney.com/zjlx/",
    }
    last_error: Exception | None = None
    payload: dict[str, Any] | None = None
    for url in EASTMONEY_MONEY_FLOW_URLS:
        try:
            candidate = _http_get_json(url, params, headers=headers)
            if (candidate.get("data") or {}).get("klines"):
                payload = candidate
                break
        except Exception as exc:
            last_error = exc
    if payload is None:
        if last_error:
            raise last_error
        return []

    data = payload.get("data") or {}
    records: list[Record] = []
    for line in data.get("klines") or []:
        fields = line.split(",")
        if len(fields) < 6:
            continue
        record = {
            "symbol": data.get("code") or _strip_exchange_prefix(symbol),
            "name": data.get("name"),
            "date": fields[0],
            "main_net_inflow": _to_float(fields[1]),
            "small_net_inflow": _to_float(fields[2]),
            "medium_net_inflow": _to_float(fields[3]),
            "large_net_inflow": _to_float(fields[4]),
            "super_large_net_inflow": _to_float(fields[5]),
        }
        if len(fields) >= 13:
            record.update(
                {
                    "main_net_inflow_pct": _to_float(fields[6]),
                    "small_net_inflow_pct": _to_float(fields[7]),
                    "medium_net_inflow_pct": _to_float(fields[8]),
                    "large_net_inflow_pct": _to_float(fields[9]),
                    "super_large_net_inflow_pct": _to_float(fields[10]),
                    "close": _to_float(fields[11]),
                    "pct_change": _to_float(fields[12]),
                }
            )
        records.append(record)
    return records


def _get_financial_report(symbol: str, report_type: str, mapping: dict[str, str]) -> list[Record]:
    source_map = {"balance": "fzb", "income": "lrb", "cash": "llb"}
    payload = _http_get_json(
        SINA_FINANCE_REPORT_URL,
        {
            "paperCode": _with_exchange_prefix(symbol),
            "source": source_map[report_type],
            "type": "0",
            "page": "1",
            "num": "1000",
        },
    )
    data = payload.get("result", {}).get("data", {})
    dates = [item["date_value"] for item in data.get("report_date", [])]
    records: list[Record] = []
    for date_text in dates:
        report = data.get("report_list", {}).get(date_text, {})
        row: Record = {
            "report_date": _iso_from_compact_date(date_text),
            "currency": report.get("rCurrency"),
        }
        for item in report.get("data", []):
            key = mapping.get(item.get("item_title", ""))
            if key:
                row[key] = _to_float(item.get("item_value"))
        records.append(row)
    return records


BALANCE_MAPPING = {
    "资产总计": "total_assets",
    "流动资产合计": "current_assets",
    "货币资金": "cash_and_equivalents",
    "存货": "inventory",
    "交易性金融资产": "current_investments",
    "应收票据及应收账款": "trade_and_non_trade_receivables",
    "非流动资产合计": "non_current_assets",
    "固定资产": "property_plant_and_equipment",
    "商誉": "goodwill_and_intangible_assets",
    "长期股权投资": "investments",
    "其他非流动金融资产": "non_current_investments",
    "实收资本(或股本)": "outstanding_shares",
    "递延所得税资产": "tax_assets",
    "负债合计": "total_liabilities",
    "流动负债合计": "current_liabilities",
    "短期借款": "current_debt",
    "应付票据及应付账款": "trade_and_non_trade_payables",
    "合同负债": "deferred_revenue",
    "吸收存款及同业存放": "deposit_liabilities",
    "非流动负债合计": "non_current_liabilities",
    "长期借款": "non_current_debt",
    "递延所得税负债": "tax_liabilities",
    "所有者权益(或股东权益)合计": "shareholders_equity",
    "股东权益合计": "shareholders_equity",
    "未分配利润": "retained_earnings",
    "其他综合收益": "accumulated_other_comprehensive_income",
    "应收账款": "accounts_receivable",
    "预付款项": "prepayments",
    "其他应收款": "other_receivables",
    "固定资产净值": "fixed_assets_net",
    "在建工程": "construction_in_progress",
    "资本公积": "capital_reserve",
    "少数股东权益": "minority_interest",
}

INCOME_MAPPING = {
    "一、营业收入": "operating_revenue",
    "营业收入": "operating_revenue",
    "二、营业支出": "total_operating_costs",
    "营业总成本": "total_operating_costs",
    "营业成本": "cost_of_revenue",
    "销售费用": "selling_general_and_administrative_expenses",
    "管理费用": "operating_expense",
    "研发费用": "research_and_development",
    "利息支出": "interest_expense",
    "营业利润": "operating_profit",
    "利润总额": "ebit",
    "减:所得税费用": "income_tax_expense",
    "所得税费用": "income_tax_expense",
    "净利润": "net_income",
    "归属于母公司所有者的净利润": "net_income_common_stock",
    "少数股东损益": "net_income_non_controlling_interests",
    "基本每股收益": "earnings_per_share",
    "稀释每股收益": "earnings_per_share_diluted",
    "投资收益": "investment_income",
    "公允价值变动收益": "fair_value_adjustments",
    "资产减值损失": "asset_impairment_loss",
    "财务费用": "financial_expenses",
    "税金及附加": "taxes_and_surcharges",
    "其他综合收益": "other_comprehensive_income",
    "综合收益总额": "total_comprehensive_income",
}

CASH_FLOW_MAPPING = {
    "经营活动产生的现金流量净额": "net_cash_flow_from_operations",
    "购建固定资产、无形资产和其他长期资产支付的现金": "capital_expenditure",
    "取得子公司及其他营业单位支付的现金净额": "business_acquisitions_and_disposals",
    "投资活动产生的现金流量净额": "net_cash_flow_from_investing",
    "取得借款收到的现金": "issuance_or_repayment_of_debt_securities",
    "吸收投资收到的现金": "issuance_or_purchase_of_equity_shares",
    "筹资活动产生的现金流量净额": "net_cash_flow_from_financing",
    "现金及现金等价物净增加额": "change_in_cash_and_equivalents",
    "汇率变动对现金及现金等价物的影响": "effect_of_exchange_rate_changes",
    "期末现金及现金等价物余额": "ending_cash_balance",
    "销售商品、提供劳务收到的现金": "cash_from_sales",
    "收到的税费返还": "tax_refunds_received",
    "支付给职工以及为职工支付的现金": "cash_paid_to_employees",
    "支付的各项税费": "taxes_paid",
    "经营活动现金流入小计": "total_cash_inflow_from_operations",
    "经营活动现金流出小计": "total_cash_outflow_from_operations",
    "收回投资所收到的现金": "cash_from_investment_recovery",
    "取得投资收益收到的现金": "cash_from_investment_income",
    "处置固定资产、无形资产收回的现金": "cash_from_asset_sales",
    "投资活动现金流入小计": "total_cash_inflow_from_investing",
    "投资活动现金流出小计": "total_cash_outflow_from_investing",
    "分配股利、利润或偿付利息所支付的现金": "cash_paid_for_dividends_and_interest",
    "偿还债务支付的现金": "cash_paid_for_debt_repayment",
    "筹资活动现金流入小计": "total_cash_inflow_from_financing",
    "筹资活动现金流出小计": "total_cash_outflow_from_financing",
    "期初现金及现金等价物余额": "beginning_cash_balance",
    "现金的期末余额": "ending_cash",
    "现金等价物的期末余额": "ending_cash_equivalents",
}


def _get_inner_trade_records(symbol: str) -> list[Record]:
    payload = _http_get_json(
        XUEQIU_INSIDER_URL,
        {"size": "100000", "page": "1", "extend": "true"},
        headers={
            "Referer": "https://xueqiu.com/hq",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    target = _with_exchange_prefix(symbol).upper()
    rows = payload.get("data", {}).get("items", []) or []
    records: list[Record] = []
    for row in rows:
        if isinstance(row, dict):
            row_symbol = str(row.get("symbol") or "")
            issuer = row.get("name")
            insider = row.get("share_changer_name")
            timestamp_ms = row.get("chg_date")
            shares_changed = _to_float(row.get("chg_shares_num"))
            avg_price = _to_float(row.get("trans_avg_price"))
            shares_after = _to_float(row.get("daily_shares_balance_otd"))
            relationship = row.get("rr_of_chgr_and_manage")
            title = row.get("duty")
        else:
            if len(row) < 10:
                continue
            row_symbol = str(row[0])
            issuer = row[1]
            insider = row[2]
            timestamp_ms = row[4]
            shares_changed = _to_float(row[5])
            avg_price = _to_float(row[6])
            shares_after = _to_float(row[7])
            relationship = row[8]
            title = row[9]
        if row_symbol != target:
            continue
        transaction_date = None
        if timestamp_ms:
            transaction_date = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).astimezone(CN_TZ)
        records.append(
            {
                "symbol": _strip_exchange_prefix(row_symbol),
                "issuer": issuer,
                "name": insider,
                "title": title,
                "transaction_date": transaction_date.date().isoformat() if transaction_date else None,
                "transaction_shares": shares_changed,
                "transaction_price_per_share": avg_price,
                "shares_owned_after_transaction": shares_after,
                "relationship": relationship,
                "is_board_director": ("董事" in str(title)) if title is not None else None,
                "transaction_value": (
                    shares_changed * avg_price
                    if shares_changed is not None and avg_price is not None
                    else None
                ),
                "shares_owned_before_transaction": (
                    shares_after - shares_changed
                    if shares_after is not None and shares_changed is not None
                    else None
                ),
            }
        )
    return records


def _get_financial_metrics_records(symbol: str) -> list[Record]:
    balances = _get_financial_report(symbol, "balance", BALANCE_MAPPING)
    incomes = _get_financial_report(symbol, "income", INCOME_MAPPING)
    cash_flows = _get_financial_report(symbol, "cash", CASH_FLOW_MAPPING)
    by_date: dict[str, Record] = {}
    for dataset in (balances, incomes, cash_flows):
        for row in dataset:
            report_date = row.get("report_date")
            if not report_date:
                continue
            target = by_date.setdefault("".join(str(report_date).split("T")[:1]), {"report_date": report_date})
            target.update({key: value for key, value in row.items() if key not in {"currency"}})
    return [by_date[key] for key in sorted(by_date, reverse=True)]


def _last_weekday(value: date) -> date:
    current = value
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def _health_check(name: str, func: Any) -> Record:
    started = datetime.now(CN_TZ)
    try:
        sample = func()
        return {
            "source": name,
            "ok": True,
            "elapsed_ms": int((datetime.now(CN_TZ) - started).total_seconds() * 1000),
            "rows": len(sample) if isinstance(sample, list) else None,
            "error": None if sample else "empty response",
        }
    except Exception as exc:
        return {
            "source": name,
            "ok": False,
            "elapsed_ms": int((datetime.now(CN_TZ) - started).total_seconds() * 1000),
            "rows": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


@mcp.tool
def get_hist_data(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    interval: Annotated[
        Literal["minute", "hour", "day", "week", "month", "year"],
        Field(description="Time interval"),
    ] = "day",
    interval_multiplier: Annotated[
        int, Field(description="Interval multiplier", ge=1)
    ] = 1,
    start_date: Annotated[
        str, Field(description="Start date in YYYY-MM-DD format")
    ] = "1970-01-01",
    end_date: Annotated[
        str, Field(description="End date in YYYY-MM-DD format")
    ] = "2030-12-31",
    adjust: Annotated[
        Literal["none", "qfq", "hfq"], Field(description="Adjustment type")
    ] = "none",
    source: Annotated[
        Literal["eastmoney", "eastmoney_direct", "sina"],
        Field(description="Data source"),
    ] = "sina",
    indicators_list: Annotated[
        list[
            Literal[
                "SMA",
                "EMA",
                "RSI",
                "MACD",
                "BOLL",
                "STOCH",
                "ATR",
                "CCI",
                "ADX",
                "WILLR",
                "AD",
                "ADOSC",
                "OBV",
                "MOM",
                "SAR",
                "TSF",
                "APO",
                "AROON",
                "AROONOSC",
                "BOP",
                "CMO",
                "DX",
                "MFI",
                "MINUS_DI",
                "MINUS_DM",
                "PLUS_DI",
                "PLUS_DM",
                "PPO",
                "ROC",
                "ROCP",
                "ROCR",
                "ROCR100",
                "TRIX",
                "ULTOSC",
            ]
        ]
        | None,
        Field(description="Technical indicators to add"),
    ] = None,
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 100,
) -> str:
    """Get historical stock market data."""
    records = _get_hist_data(
        symbol=symbol,
        interval=interval,
        interval_multiplier=interval_multiplier,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust,
    )
    if indicators_list:
        _add_indicators(records, indicators_list)
    if recent_n is not None:
        records = records[-recent_n:]
    return _json_records(records)


@mcp.tool
def get_realtime_data(
    symbol: Annotated[
        str | None, Field(description="Stock symbol/ticker (e.g. '000001')")
    ] = None,
    source: Annotated[
        Literal["sina", "tencent", "xueqiu", "eastmoney", "eastmoney_direct"],
        Field(description="Data source"),
    ] = "sina",
) -> str:
    """Get real-time stock market data."""
    records = _get_realtime_data(symbol=symbol, source=source)
    return _json_records(records)


@mcp.tool
def get_stock_snapshot(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
) -> str:
    """Get detailed stock quote snapshot with bid/ask levels."""
    return _json_records([_get_stock_snapshot_record(symbol)])


@mcp.tool
def get_index_data(
    symbols: Annotated[
        list[str] | None,
        Field(description="Index symbols or aliases, e.g. ['sh000001','399006','csi300']"),
    ] = None,
) -> str:
    """Get realtime index quotes for common China A-share indices."""
    if symbols is None:
        symbols = ["sh000001", "sz399001", "sz399006", "sh000300", "sh000905"]
    return _json_records(_get_index_records(symbols))


@mcp.tool
def get_news_data(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """Get stock-related news data."""
    records = _get_news_records(symbol)
    if recent_n is not None:
        records = records[-recent_n:]
    return _json_records(records)


@mcp.tool
def get_announcement_data(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    category: Annotated[
        Literal[
            "all",
            "financial_report",
            "financing",
            "risk",
            "info_change",
            "major_event",
            "restructuring",
            "shareholding_change",
        ],
        Field(description="Announcement category"),
    ] = "all",
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """Get company announcements from EastMoney."""
    return _json_records(_get_announcement_records(symbol, category, recent_n))


@mcp.tool
def get_money_flow_data(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 20,
) -> str:
    """Get daily stock money flow data from EastMoney."""
    records = _get_money_flow_records(symbol)
    if recent_n is not None:
        records = records[-recent_n:]
    return _json_records(records)


@mcp.tool
def get_balance_sheet(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """Get company balance sheet data."""
    records = _get_financial_report(symbol, "balance", BALANCE_MAPPING)
    if recent_n is not None:
        records = records[:recent_n]
    return _json_records(records)


@mcp.tool
def get_income_statement(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """Get company income statement data."""
    records = _get_financial_report(symbol, "income", INCOME_MAPPING)
    if recent_n is not None:
        records = records[:recent_n]
    return _json_records(records)


@mcp.tool
def get_cash_flow(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    source: Annotated[Literal["sina"], Field(description="Data source")] = "sina",
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """Get company cash flow statement data."""
    records = _get_financial_report(symbol, "cash", CASH_FLOW_MAPPING)
    if recent_n is not None:
        records = records[:recent_n]
    return _json_records(records)


@mcp.tool
def get_inner_trade_data(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
) -> str:
    """Get company insider trading data."""
    return _json_records(_get_inner_trade_records(symbol))


@mcp.tool
def get_financial_metrics(
    symbol: Annotated[str, Field(description="Stock symbol/ticker (e.g. '000001')")],
    recent_n: Annotated[
        int | None, Field(description="Number of most recent records to return", ge=1)
    ] = 10,
) -> str:
    """
    Get key financial metrics from the three major financial statements.
    """
    records = _get_financial_metrics_records(symbol)
    if recent_n is not None:
        records = records[:recent_n]
    return _json_records(records)


@mcp.tool
def get_time_info() -> dict:
    """Get current time with ISO format, timestamp, and the last trading day."""
    local_time = datetime.now().astimezone()
    last_trading_day = _last_weekday(local_time.date()).isoformat()

    return {
        "iso_format": local_time.isoformat(),
        "timestamp": local_time.timestamp(),
        "last_trading_day": last_trading_day,
    }


@mcp.tool
def get_api_health(
    symbol: Annotated[str, Field(description="Stock symbol/ticker used for probe")] = "600519",
) -> str:
    """Check availability of the lightweight upstream APIs."""
    checks = [
        _health_check("sina_realtime", lambda: _get_sina_realtime_data(symbol)),
        _health_check("tencent_realtime", lambda: _get_tencent_realtime_data(symbol)),
        _health_check("tencent_snapshot", lambda: [_get_stock_snapshot_record(symbol)]),
        _health_check("tencent_index", lambda: _get_index_records(["sh000001"])),
        _health_check(
            "tencent_hist",
            lambda: _get_hist_data(
                symbol=symbol,
                interval="day",
                interval_multiplier=1,
                start_date="2026-07-14",
                end_date="2026-07-20",
                adjust="none",
            ),
        ),
        _health_check("eastmoney_news", lambda: _get_news_records(symbol)[:1]),
        _health_check(
            "eastmoney_announcement",
            lambda: _get_announcement_records(symbol, "all", 1),
        ),
        _health_check("eastmoney_money_flow", lambda: _get_money_flow_records(symbol)[-1:]),
        _health_check(
            "sina_financial_report",
            lambda: _get_financial_report(symbol, "balance", BALANCE_MAPPING)[:1],
        ),
        _health_check("xueqiu_inner_trade", lambda: _get_inner_trade_records(symbol)[:1]),
    ]
    return _json_records(checks)
