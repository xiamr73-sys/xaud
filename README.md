# 加密货币趋势监控系统

这是一个基于 Flask 的实时加密货币趋势监控系统，具备以下特性：
- **多维度分析**：结合 EMA 趋势、ADX 强度、成交量分布 (POC)、资金费率和持仓量 (OI) 分析。
- **智能评分**：根据 ADX、成交量和 OI 变化计算 TrendScore，筛选 Top 3 机会。
- **交易计划**：点击卡片自动计算基于 ATR 的动态止盈止损点位。
- **实时更新**：后台每 5 分钟自动更新，支持手动刷新。

## 部署指南

### 1. 本地运行

安装依赖：
```bash
pip install -r requirements.txt
```

启动应用：
```bash
python monitor_app.py
```
访问 http://127.0.0.1:5001

### 2. 部署到 Render / Heroku

本项目已准备好 `Procfile` 和 `requirements.txt`，可直接部署到 PaaS 平台。

**Render 部署步骤：**
1. 将代码推送到 GitHub。
2. 在 Render 创建新的 Web Service。
3. 连接你的 GitHub 仓库。
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn monitor_app:app`
6. 点击 Deploy。

### 3. Docker 部署

构建镜像：
```bash
docker build -t crypto-monitor .
```

运行容器：
```bash
docker run -p 5001:5001 -e PORT=5001 crypto-monitor
```

## 注意事项
- 本项目使用 Binance 公共 API，无需 API Key 即可获取行情数据。
- 如需更高频次请求，建议在代码中配置自己的 API Key。
