# 必须使用 3.12 以满足最新依赖包的要求
FROM python:3.12-slim

# 安装 git (防止 pip install 需要从 github 拉取代码) 和构建工具
# 注意：apt-get install 参数应该是 --no-install-recommends 而不是 --no-install-recommended
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目余下文件
COPY . .

# 适配你之前在 GCP 设置的 5001 端口
ENV PORT=5001
EXPOSE 5001

CMD ["python", "monitor_app.py"]