# Crypto Alpha Monitor

这是一个基于 Python 的高频加密货币监控工具，旨在捕捉与 BTC 走势脱节的“Alpha”机会。

## 功能特点

- **全自动监控**：自动筛选 Binance 合约交易量前 200 的币种。
- **多维度分析**：
  - **相对强度 (RS)**：实时计算山寨币与 BTC 的涨跌幅差值。
  - **资金流向 (OI)**：监控持仓量异动，识别资金入场信号。
  - **量价配合**：结合成交量确认突破有效性。
- **智能筛选**：
  - **多头信号**：BTC 企稳/回调 + 山寨币强势 + OI 上升。
  - **空头信号**：BTC 上涨/微跌 + 山寨币弱势 + OI 上升。
- **实时推送**：通过 Discord Webhook 发送结构化交易信号。

## 依赖库

请确保安装以下 Python 库：

```bash
pip install ccxt aiohttp
```

## 配置说明

在 `crypto_alpha_monitor.py` 文件头部配置您的参数：

```python
# Discord Webhook (必填)
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."

# 监控参数
CHECK_INTERVAL = 60  # 扫描间隔 (秒)
TIMEFRAME = '1h'     # 价格对比周期
OI_TIMEFRAME = '1h'  # 持仓量对比周期
```

## 运行方式

```bash
python crypto_alpha_monitor.py
```

## 策略逻辑详解

1. **基准锚定**：计算 BTC 在当前周期（如 1h）内的涨跌幅。
2. **个币对比**：计算每个目标币种的同期涨跌幅。
3. **相对强度 (RS)** = `个币涨幅` - `BTC涨幅`。
4. **持仓量变化** = `(当前OI - 历史OI) / 历史OI`。
5. **信号触发**：
   - 当 `RS` 和 `OI` 同时满足特定阈值（如 RS > 1%, OI > 3%）时，触发报警。

## 注意事项

- 程序默认使用 Binance 合约接口，无需 API Key 即可获取公开行情数据（Ticker, K线, OI）。
- 如需更高频次监控或交易功能，建议配置 API Key 并启用 WebSocket。
