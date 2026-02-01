# 使用 Python 3.9 作为基础镜像 (兼容性好)
FROM python:3.9-slim

# 安装系统依赖 (git 用于某些 pip 包)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 设置权限
RUN chmod +x start.sh

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

# 暴露端口
EXPOSE 5001

# 启动脚本
CMD ["./start.sh"]
