# Serverless 部署指南 (无需后台)

您选择了“无后台”方案，这意味着我们不再依赖持续运行的服务器（如 Cloud Run 或 VPS），而是将其部署到 **Vercel** 这样的 Serverless 平台。

**核心变化**：
- **移除后台线程**：应用不再自动每 5 分钟刷新数据。
- **触发式更新**：
    - **方式 A (手动)**：当您打开网页时，如果数据过期，点击“刷新”按钮。
    - **方式 B (自动)**：使用免费的定时服务（如 UptimeRobot）每 5 分钟访问一次刷新接口。

## 部署步骤 (Vercel)

Vercel 提供永久免费的 Python 托管服务，非常适合此项目。

### 1. 准备代码
确保代码已推送到 GitHub。

### 2. 导入到 Vercel
1.  注册/登录 [Vercel.com](https://vercel.com)。
2.  点击 **"Add New..."** -> **"Project"**。
3.  选择您的 GitHub 仓库并点击 **Import**。

### 3. 配置项目
在部署配置页：
*   **Framework Preset**: 选择 `Other`。
*   **Environment Variables** (环境变量):
    *   `BINANCE_API_KEY`: 您的 API Key
    *   `BINANCE_SECRET_KEY`: 您的 Secret Key

点击 **Deploy**。

### 4. 设置自动刷新 (可选但推荐)
由于 Serverless 不会自动运行，为了让您打开页面时能立刻看到最新数据（而不是等待十几秒），建议设置一个外部定时器。

1.  注册 [UptimeRobot](https://uptimerobot.com) (免费)。
2.  点击 **"Add New Monitor"**。
3.  **Monitor Type**: HTTP(s).
4.  **Friendly Name**: Crypto Refresh.
5.  **URL (or IP)**: `https://您的Vercel域名.vercel.app/api/refresh`
6.  **Monitoring Interval**: 5 minutes.
7.  点击 **Create Monitor**。

这样，UptimeRobot 会每 5 分钟帮您“点击”一次刷新接口，确保数据永远是最新的。

## 常见问题
*   **刷新慢？**: Serverless 实例可能会冷启动，且分析 300 个币种需要时间。建议在 UptimeRobot 设置超时时间长一点。
*   **数据空白？**: 刚部署完第一次访问可能是空白的，请点击页面上的“立即刷新”或等待 UptimeRobot 触发第一次更新。
