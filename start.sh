#!/bin/bash

# 启动监控进程 (后台运行)
echo "Starting Monitor..."
python3 binance_futures_monitor/monitor.py &

# 启动 Web 服务器 (前台运行)
echo "Starting Web Server..."
python3 binance_futures_monitor/web_server.py
