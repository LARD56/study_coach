FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY docs/ ./docs/
COPY main.py .

# 创建必要的目录
RUN mkdir -p data/knowledge logs

# 环境变量 (通过 --env-file 传入)
ENV PYTHONUNBUFFERED=1

# 默认命令
CMD ["python", "main.py", "--help"]