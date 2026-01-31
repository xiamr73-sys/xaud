# 必须使用 Python 3.12 镜像，因为你的依赖库（如 pandas 相关版本）要求 3.12+ 
FROM python:3.12-slim

# 安装构建依赖（部分加密货币库编译时需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制并安装依赖
COPY requirements.txt .
# 关键：确保安装 pandas_ta，如果报错，请检查 requirements.txt 里的拼写是否为 pandas-ta
# 增加 git 是因为我们从 git 安装 pandas_ta
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 适配 Cloud Run 端口
ENV PORT=5001
EXPOSE 5001

CMD ["python", "monitor_app.py"]