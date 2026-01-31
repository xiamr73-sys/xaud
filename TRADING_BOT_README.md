# 量化交易机器人 (Trading Bot)

这是一个基于 `monitor_app.py` 信号的自动化交易程序。

## 功能
- **自动获取信号**: 从本地运行的监控服务 (`http://127.0.0.1:5001/api/data`) 获取 "Strong Long" 或 "Strong Short" 的币种。
- **自动下单**:
    - 自动设置杠杆 (默认 5x)。
    - 市价开仓 (Market Order)。
    - 自动挂止损单 (Stop Loss Market)。
    - 自动挂止盈单 (Take Profit Market)。
- **安全机制**:
    - **DRY_RUN (模拟模式)**: 默认开启，只打印日志，不执行真实交易。
    - **最大持仓限制**: 限制同时持有的仓位数量 (默认 3)。
    - **资金管理**: 限制每笔交易的 USDT 金额。

## 快速开始

### 1. 配置
打开 `trading_bot.py`，修改顶部的配置部分：

```python
# Trading Settings
DRY_RUN = True  # 设置为 False 以执行真实交易
MAX_OPEN_POSITIONS = 3
LEVERAGE = 5
USDT_PER_TRADE = 20.0  # 每笔交易使用的 USDT 金额
```

确保 `.env` 文件中包含您的 Binance API Key：
```bash
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
```

### 2. 运行
确保 `monitor_app.py` 正在运行，然后启动机器人：

```bash
python3 trading_bot.py
```

### 3. 查看日志
机器人会输出日志到控制台，并保存到 `trading_bot.log` 文件中。

## 注意事项
- 本程序仅供学习和参考，实盘交易请务必做好风险控制。
- 建议先在 Binance 测试网或使用小资金进行测试。
