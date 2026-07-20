# AKShare One MCP 服务器

<div align="center">
  <a href="README.md">English</a> |
  <a href="README_zh.md">中文</a>
</div>

这是一个轻量级 MCP (Model Context Protocol) 服务器，为中国股票市场提供常用数据接口服务。默认运行路径使用标准库 HTTP 直连公开数据源，不依赖 `akshare`、`pandas`、`numpy`，适合在树莓派 Zero 2W 这类低资源设备上以 stdio 模式运行。

当前轻量运行时使用的数据源：

- 腾讯：历史 K 线、个股详细快照、指数行情和实时行情备用源
- 新浪：实时行情和财务报表
- 东方财富：股票新闻、公司公告和资金流向
- 雪球：内部交易数据

## 功能特性

- **历史数据**: 获取股票历史行情数据，支持多种时间周期和复权方式
- **实时数据**: 提供实时股票行情信息
- **新闻资讯**: 获取股票相关的最新新闻资讯
- **公司公告**: 获取上市公司公告，支持财务报告、重大事项、风险提示等分类
- **资金流向**: 获取个股日级主力、大单、中单、小单资金流向
- **财务报表**: 查看公司资产负债表、利润表、现金流量表
- **分析指标**: 计算关键财务指标和技术分析指标

## 工具说明

### 市场数据

#### `get_index_data` - 获取指数行情

<details>
<summary>参数说明</summary>

- `symbols` (list, 可选): 指数代码或别名，例如 `sh000001`、`399001`、`399006`、`csi300`、`csi500`、`csi1000`；默认返回主要指数

</details>

#### `get_hist_data` - 获取历史股票数据
获取指定股票的历史行情数据，支持多种数据源和复权方式。

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码，如 '000001'
- `interval` (string, 可选): 时间周期，可选值：'minute'(分钟)、'hour'(小时)、'day'(日线)、'week'(周线)、'month'(月线)、'year'(年线)，默认 'day'
- `start_date` (string, 可选): 开始日期，格式：YYYY-MM-DD，默认 '1970-01-01'
- `end_date` (string, 可选): 结束日期，格式：YYYY-MM-DD，默认 '2030-12-31'
- `adjust` (string, 可选): 复权方式，'none'(不复权)、'qfq'(前复权)、'hfq'(后复权)，默认 'none'
- `source` (string, 可选): 兼容参数；当前轻量实现使用腾讯行情接口获取历史 K 线
- `indicators_list` (list, 可选): 技术指标列表；轻量实现原生支持 SMA、EMA、RSI、MACD、BOLL
- `recent_n` (number, 可选): 返回最新记录数，默认 100

</details>

#### `get_realtime_data` - 获取实时股票数据

<details>
<summary>参数说明</summary>

- `symbol` (string, 可选): 股票代码，留空获取所有股票概览
- `source` (string, 可选): 数据源，'sina'(新浪)、'tencent'(腾讯)，默认 'sina'；旧参数 'xueqiu'、'eastmoney'、'eastmoney_direct' 会自动走轻量可用源兜底

</details>

#### `get_stock_snapshot` - 获取个股详细快照

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码

</details>

### 新闻资讯

#### `get_news_data` - 获取股票新闻

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

#### `get_announcement_data` - 获取公司公告

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `category` (string, 可选): 公告分类，可选值：'all'、'financial_report'、'financing'、'risk'、'info_change'、'major_event'、'restructuring'、'shareholding_change'，默认 'all'
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

### 资金流向

#### `get_money_flow_data` - 获取个股资金流向

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `recent_n` (number, 可选): 返回最新记录数，默认 20

</details>

### 财务报表

#### `get_balance_sheet` - 获取资产负债表

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

#### `get_income_statement` - 获取利润表

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

#### `get_cash_flow` - 获取现金流量表


<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `source` (string, 可选): 兼容参数；轻量实现使用新浪财报接口
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

### 分析指标

#### `get_inner_trade_data` - 获取内部交易数据


<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码

</details>

#### `get_financial_metrics` - 获取财务指标

<details>
<summary>参数说明</summary>

- `symbol` (string, 必填): 股票代码
- `recent_n` (number, 可选): 返回最新记录数，默认 10

</details>

#### `get_time_info` - 获取时间信息

获取当前时间、时间戳和最近一个交易日信息。

> 轻量实现会把 `last_trading_day` 估算为最近一个工作日，不识别交易所节假日。

#### `get_api_health` - 检查数据源可用性

使用指定股票代码探测新浪实时、腾讯实时、腾讯历史 K 线、东方财富新闻、东方财富公告、新浪财报、雪球内部交易等轻量上游接口是否可用。

<details>
<summary>参数说明</summary>

- `symbol` (string, 可选): 用于探测的股票代码，默认 '600519'

</details>


## 运行模式

服务器支持两种运行模式：**stdio** 和 **streamable-http**

### 命令行参数
- `--streamable-http`: 启用 HTTP 模式 (默认为 stdio 模式)
- `--host`: HTTP 模式绑定的主机地址 (默认: 0.0.0.0)
- `--port`: HTTP 模式监听的端口 (默认: 8081)

> **说明:** 启用 streamable-http 模式后，MCP 服务器将在 `http://{host}:{port}/mcp` 提供服务。默认地址为 `http://0.0.0.0:8081/mcp`

### 树莓派 Zero 2W 建议

树莓派上建议优先使用默认 stdio 模式：

```bash
uv sync --no-dev
uv run akshare-one-mcp
```

默认依赖只安装 MCP 运行所需包，不安装 `akshare`、`pandas`、`numpy`、`lxml`、`mini-racer` 等重依赖。如果需要 HTTP 模式，再安装 `http` extra：

```bash
uv sync --no-dev --extra http
uv run akshare-one-mcp --streamable-http --host 0.0.0.0 --port 8081
```

保留了 `legacy-akshare` extra 作为兼容选项，但树莓派 Zero 2W 不建议启用：

```bash
uv sync --extra legacy-akshare
```

## 安装指南

### Hermes / MCP 客户端配置

如果尚未安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)，请先安装。

Hermes 或其他兼容标准 `mcpServers` 配置的 MCP 客户端可以直接使用本地 stdio 配置：

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

也可以用 `uvx` 直接从你的 GitHub 仓库运行：

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

### 通过代码库本地安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/MCU-UAV/akshare-one-mcp.git
   cd akshare-one-mcp
   ```

2. **安装依赖**
   ```bash
   uv sync --no-dev
   ```

3. **配置 MCP 客户端**
   ```json
   {
     "mcpServers": {
       "akshare-one-mcp": {
         "command": "uv",
         "args": [
           "--directory",
           "/path/to/akshare-one-mcp",
           "run",
           "akshare-one-mcp"
         ]
       }
     }
   }
   ```

### Hermes HTTP 模式

如需在树莓派或服务器上常驻 HTTP 服务：

```bash
uv sync --no-dev --extra http
uv run akshare-one-mcp --streamable-http --host 0.0.0.0 --port 8081
```

然后在 Hermes 中配置远程 MCP 地址：

```text
http://<host>:8081/mcp
```

如果你的 Hermes 版本要求用 JSON 配置 HTTP MCP 服务，可以使用等价写法：

```json
{
  "mcpServers": {
    "akshare-one-mcp": {
      "url": "http://<host>:8081/mcp"
    }
  }
}
```

## 技术指标

`get_hist_data` 轻量实现当前原生支持下面这些技术指标：

- `SMA`: 简单移动平均
- `EMA`: 指数移动平均
- `RSI`: 相对强弱指数
- `MACD`: 指数平滑异同移动平均线，返回 `macd`、`signal`、`histogram`
- `BOLL`: 布林带，返回 `boll_upper`、`boll_middle`、`boll_lower`

其他指标参数会被忽略，以避免引入 TA-Lib、pandas、numpy 等重依赖。
