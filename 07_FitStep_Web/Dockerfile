# ─── Stage 1: dependency builder ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# chromadb 컴파일에 build-essential 필요 → builder 단계에만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY 07_FitStep_Web/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# builder에서 설치된 패키지만 복사 (build-essential 미포함)
COPY --from=builder /install /usr/local

# 앱 소스 복사 (secrets.toml은 제외 — env vars로 주입)
# build context는 ax-workspace/ 루트 기준
COPY 07_FitStep_Web/app.py 07_FitStep_Web/api_client.py 07_FitStep_Web/requirements.txt ./
COPY 07_FitStep_Web/themes/ ./themes/

# app.py가 ../06_FitStep/rag/ 를 sys.path로 참조하므로 동일한 상대 경로로 복사
COPY 06_FitStep/rag/ /06_FitStep/rag/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
