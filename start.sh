#!/bin/bash
set -e

# 启动监控进程 (后台运行)
echo "Starting Monitor..."
# 使用 nohup 确保后台进程稳定，虽在容器中非必须但更保险
# 重定向输出到标准输出，以便 Cloud Logging 采集
python3 binance_futures_monitor/monitor.py &

# 启动 Web 服务器 (前台运行)
# 使用 exec 让 web server 成为主进程，接收系统信号 (如 SIGTERM)
echo "Starting Web Server..."
exec python3 binance_futures_monitor/web_server.py
