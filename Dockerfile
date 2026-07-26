# ── Stage 1: 前端构建 ──────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: 后端运行 ──────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# 系统依赖（FunASR 音频处理需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen

# 源码
COPY main.py ./
COPY backend/ ./backend/
COPY tests/ ./tests/

# 前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 运行时目录
RUN mkdir -p data uploads/jd uploads/resume uploads/temp_resume uploads/avatars uploads/voice interviews

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uv", "run", "python", "main.py"]
