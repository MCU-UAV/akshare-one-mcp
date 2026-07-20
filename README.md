# AKShare One MCP Server

<div align="center">
  <a href="README.md">English</a> | 
  <a href="README_zh.md">中文</a>
</div>

<!-- mcp-name: io.github.MCU-UAV/akshare-one-mcp -->

## Overview

A lightweight MCP server for common China stock market data. The default runtime uses Python standard-library HTTP clients against public data sources and does not require `akshare`, `pandas`, `numpy`, `lxml`, `mini-racer`, or `requests`. It is suitable for low-resource devices such as Raspberry Pi Zero 2W running MCP over stdio.

Data sources currently used by the lightweight runtime:

- Tencent: historical K-line, detailed stock snapshots, index quotes, and fallback realtime quotes
- Sina: realtime quotes and financial reports
- EastMoney: stock news, company announcements, and money flow
- Xueqiu: insider trading data

## Available Tools

### Market Data Tools

#### `get_index_data`
Get realtime quotes for common China A-share indices.

<details>
<summary>Parameters</summary>

- `symbols` (list, optional): Index symbols or aliases. Examples: `sh000001`, `399001`, `399006`, `csi300`, `csi500`, `csi1000`. Defaults to major indices.

</details>

#### `get_hist_data`
Get historical stock market data with support for multiple time periods and adjustment methods.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code (e.g. '000001')
- `interval` (string, optional): Time interval ('minute','hour','day','week','month','year') (default: 'day')
- `interval_multiplier` (number, optional): Interval multiplier (default: 1)
- `start_date` (string, optional): Start date in YYYY-MM-DD format (default: '1970-01-01')
- `end_date` (string, optional): End date in YYYY-MM-DD format (default: '2030-12-31')
- `adjust` (string, optional): Adjustment type ('none', 'qfq', 'hfq') (default: 'none')
- `source` (string, optional): Compatibility parameter; the lightweight runtime currently uses Tencent K-line data
- `indicators_list` (list, optional): Technical indicators to add; lightweight runtime supports `SMA`, `EMA`, `RSI`, `MACD`, `BOLL`
- `recent_n` (number, optional): Number of most recent records to return (default: 100)

</details>

#### `get_realtime_data`
Get real-time stock market data.

<details>
<summary>Parameters</summary>

- `symbol` (string, optional): Stock code
- `source` (string, optional): Data source (`sina`, `tencent`) (default: `sina`); legacy values `xueqiu`, `eastmoney`, and `eastmoney_direct` fall back to a lightweight available source

</details>

#### `get_stock_snapshot`
Get detailed stock quote snapshot with bid/ask levels.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code

</details>

### News & Information Tools

#### `get_news_data`
Get stock-related news data.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

#### `get_announcement_data`
Get listed-company announcements from EastMoney.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `category` (string, optional): Announcement category. One of `all`, `financial_report`, `financing`, `risk`, `info_change`, `major_event`, `restructuring`, `shareholding_change` (default: `all`)
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

### Capital Flow Tools

#### `get_money_flow_data`
Get daily stock money flow data from EastMoney.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `recent_n` (number, optional): Number of most recent records to return (default: 20)

</details>

### Financial Statement Tools

#### `get_balance_sheet`
Get company balance sheet data.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

#### `get_income_statement`
Get company income statement data.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

#### `get_cash_flow`
Get company cash flow statement data.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `source` (string, optional): Compatibility parameter; lightweight runtime uses Sina financial reports
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

### Analysis & Metrics Tools

#### `get_inner_trade_data`
Get company insider trading data.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code

</details>

#### `get_financial_metrics`
Get key financial metrics from the three major financial statements.

<details>
<summary>Parameters</summary>

- `symbol` (string, required): Stock code
- `recent_n` (number, optional): Number of most recent records to return (default: 10)

</details>

#### `get_time_info`
Get current time with ISO format, timestamp, and the last trading day.

> The lightweight runtime estimates `last_trading_day` as the latest weekday. It does not account for exchange holidays.

#### `get_api_health`
Probe lightweight upstream API availability.

<details>
<summary>Parameters</summary>

- `symbol` (string, optional): Stock code used for probing (default: `600519`)

</details>

## Installation & Setup

### Running Modes

The server supports two modes: stdio and streamable-http

**Command Line Arguments:**
- `--streamable-http`: Enable HTTP mode (default: stdio mode)
- `--host`: Host to bind to in HTTP mode (default: 0.0.0.0)
- `--port`: Port to listen on in HTTP mode (default: 8081)

> **Note:** When using streamable-http mode, the MCP server will be available at `http://{host}:{port}/mcp`. For the default configuration, this would be `http://0.0.0.0:8081/mcp`.

### Raspberry Pi / Lightweight Stdio

For Raspberry Pi Zero 2W or other low-resource devices, prefer stdio mode:

```bash
git clone https://github.com/MCU-UAV/akshare-one-mcp.git
cd akshare-one-mcp
uv sync --no-dev
uv run akshare-one-mcp
```

The default install intentionally excludes heavy legacy data packages. If you need HTTP transport:

```bash
uv sync --no-dev --extra http
uv run akshare-one-mcp --streamable-http --host 0.0.0.0 --port 8081
```

The legacy `akshare-one` dependency remains available as an optional extra, but is not recommended on Raspberry Pi Zero 2W:

```bash
uv sync --extra legacy-akshare
```

### Hermes / MCP Client Configuration

Use this stdio configuration in Hermes or any MCP client that accepts the standard `mcpServers` format:

```json
{
  "mcpServers": {
    "akshare-one-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/akshare-one-mcp",
        "run",
        "akshare-one-mcp"
      ]
    }
  }
}
```

For a one-command GitHub install through `uvx`, use:

```json
{
  "mcpServers": {
    "akshare-one-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/MCU-UAV/akshare-one-mcp.git",
        "akshare-one-mcp"
      ]
    }
  }
}
```

For streamable HTTP, start the server separately:

```bash
uv sync --no-dev --extra http
uv run akshare-one-mcp --streamable-http --host 0.0.0.0 --port 8081
```

Then point Hermes to the streamable HTTP endpoint:

```text
http://<host>:8081/mcp
```

If your Hermes build expects JSON for HTTP MCP servers, use the equivalent URL form:

```json
{
  "mcpServers": {
    "akshare-one-mcp": {
      "url": "http://<host>:8081/mcp"
    }
  }
}
```

## Technical Indicators Reference

The lightweight `get_hist_data` implementation currently supports these indicators natively:

- `SMA`: Simple Moving Average
- `EMA`: Exponential Moving Average
- `RSI`: Relative Strength Index
- `MACD`: Moving Average Convergence Divergence, including `macd`, `signal`, and `histogram`
- `BOLL`: Bollinger Bands, including `boll_upper`, `boll_middle`, and `boll_lower`

Other accepted indicator names are ignored to avoid pulling in TA-Lib, pandas, or numpy.
