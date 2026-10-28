# syntax=docker/dockerfile:1.7

# ---- web: static Next.js export -------------------------------------------------
FROM --platform=$BUILDPLATFORM node:22-bookworm-slim AS web
RUN npm install -g pnpm@9.15.0
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web ./
RUN pnpm build

# ---- build: resolve deps and bake the embedding model ---------------------------
FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev
ENV MODEL_CACHE=/opt/models
RUN /app/.venv/bin/python -c "from behique.embed import Embedder; from behique import tokens; \
Embedder().embed_query('warm up'); tokens.count('warm up')"

# ---- runtime ---------------------------------------------------------------------
FROM python:3.12-slim-bookworm
RUN useradd --system --uid 10001 --home-dir /app behique \
 && mkdir -p /index /data \
 && chown behique /index
COPY --from=build /app /app
COPY --from=build /opt/models /opt/models
COPY --from=web /web/out /app/web
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    MODEL_CACHE=/opt/models \
    HF_HUB_OFFLINE=1 \
    DATA_ROOT=/data \
    DB_PATH=/index/behique.db \
    WEB_DIR=/app/web
USER behique
WORKDIR /app
VOLUME ["/index"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import urllib.request,os,sys; r=urllib.request.Request('http://127.0.0.1:8000/api/health', headers={'x-api-key': os.environ.get('API_KEY','')}); sys.exit(0 if urllib.request.urlopen(r, timeout=4).status == 200 else 1)"]
# 0.0.0.0 inside the container; compose publishes it on 127.0.0.1 only.
CMD ["uvicorn", "--factory", "behique.main:app", "--host", "0.0.0.0", "--port", "8000"]
