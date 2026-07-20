---
name: akshare-stock-mcp
description: Use when answering China A-share stock questions through the lightweight akshare-one-mcp server, including realtime quotes, detailed quote snapshots, index quotes, historical K-line data, money flow, stock news, company announcements, financial statements, financial metrics, insider trades, API health checks, Raspberry Pi/Hermes setup, or deciding which stock MCP tool to call.
---

# AKShare Stock MCP

Use this skill when the user wants China stock market data from this repository's lightweight MCP server or asks how to use/install it in Hermes.

## Core Rules

- Prefer MCP tools over web browsing when the requested data is available from `akshare-one-mcp`.
- Keep data retrieval atomic first, then synthesize: quote -> history -> news/announcements -> financials.
- For current data, call `get_api_health` first if the user reports failures or if multiple sources disagree.
- Treat `get_time_info.last_trading_day` as a lightweight weekday estimate, not an exchange holiday calendar.
- Avoid asking the model to infer stock codes when a company name is ambiguous; ask for the code or state the assumption.
- Keep outputs in Chinese when the user asks in Chinese.

## Tool Selection

- `get_realtime_data`: current quote. Use `source="sina"` by default; use `source="tencent"` as fallback.
- `get_stock_snapshot`: detailed quote snapshot with bid/ask levels, valuation fields, market cap, amplitude, turnover rate, and limits.
- `get_index_data`: realtime quotes for major indices such as 上证指数, 深证成指, 创业板指, 沪深300, 中证500, 中证1000.
- `get_hist_data`: K-line history and lightweight indicators. Use for trend, recent returns, moving averages, RSI, MACD, and Bollinger bands.
- `get_money_flow_data`: daily money flow from EastMoney. Use for main-force, large-order, medium-order, and small-order net inflow analysis.
- `get_news_data`: media/news search for a stock.
- `get_announcement_data`: official company announcements. Use this for material events, financial reports, risk warnings, restructuring, financing, and shareholding changes.
- `get_balance_sheet`, `get_income_statement`, `get_cash_flow`: statement-level financials.
- `get_financial_metrics`: compact cross-statement key fields.
- `get_inner_trade_data`: insider trading/management shareholding changes. Empty arrays can mean no matching records.
- `get_api_health`: upstream source availability and latency.
- `get_time_info`: current server time and latest weekday trading-day estimate.

## Common Workflows

### Quick Stock Snapshot

1. Call `get_realtime_data(symbol)`.
2. Call `get_stock_snapshot(symbol)` if the user asks about盘口, 市值, 换手率, 涨跌停, or bid/ask levels.
3. Call `get_hist_data(symbol, interval="day", recent_n=20, indicators_list=["SMA","RSI","MACD"])`.
4. Optionally call `get_money_flow_data(symbol, recent_n=5)` when the user asks about funds, main force, capital flow, or abnormal movement.
5. Summarize price, daily change, recent trend, indicator signals, and money-flow direction when available.
6. Mention source freshness and avoid investment advice wording.

### Market Index Context

1. Call `get_index_data()` for the default major index set.
2. Use index aliases such as `csi300`, `csi500`, `csi1000`, `399006`, or Chinese names when a specific index is requested.
3. Compare an individual stock against the relevant index only descriptively.

### News And Announcement Review

1. Call `get_news_data(symbol, recent_n=5)`.
2. Call `get_announcement_data(symbol, category="all", recent_n=5)`.
3. Separate media reports from official disclosures.
4. Highlight dates, source/category, and URLs.

### Money Flow Review

1. Call `get_money_flow_data(symbol, recent_n=5)` for recent daily flow.
2. Compare `main_net_inflow`, `large_net_inflow`, and `super_large_net_inflow` against price change.
3. Treat positive inflow as a descriptive signal only; do not present it as buy/sell advice.
4. Mention amounts are in yuan and percentage fields are percent values.

### Financial Check

1. Call `get_financial_metrics(symbol, recent_n=4)`.
2. If the user asks for details, call the relevant statement tool.
3. Compare newest period with earlier periods using available fields only.
4. Mark missing/null fields as unavailable, not zero.

### Troubleshooting

1. Call `get_api_health(symbol)` using a liquid stock such as `600519`.
2. If one source fails, retry with the alternate source where available.
3. For Hermes setup issues, verify the config uses either:
   - local stdio: `uv --directory /absolute/path run akshare-one-mcp`
   - GitHub uvx: `uvx --from git+https://github.com/MCU-UAV/akshare-one-mcp.git akshare-one-mcp`
   - HTTP: `http://<host>:8081/mcp` after starting with `--streamable-http`

## Output Guidance

- Always distinguish facts from interpretation.
- Include the stock code and data time when available.
- For empty arrays, say "当前接口未返回匹配数据", not "没有发生".
- For health checks, `ok=true` with `error="empty response"` means the upstream responded but the sample had no rows.
- For all-market realtime requests, warn that they can be heavier on Raspberry Pi; prefer single-symbol queries.
