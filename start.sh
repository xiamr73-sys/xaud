#!/bin/bash
set -e

# 启动统一的监控应用 (Flask + Background Thread)
echo "Starting Monitor App (Unified)..."
exec python3 monitor_app.py
