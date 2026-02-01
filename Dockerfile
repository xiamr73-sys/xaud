# 使用 Python 3.9 作为基础镜像 (兼容性好)
FROM python:3.9-slim

# 安装系统依赖 (git 用于某些 pip 包)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制并安装依赖 (仅复制 requirements.txt 以利用缓存)
COPY binance_futures_monitor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY binance_futures_monitor ./binance_futures_monitor
COPY start.sh .

# 设置权限
RUN chmod +x start.sh

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 暴露端口
EXPOSE 8080

# 启动脚本
CMD ["./start.sh"]
