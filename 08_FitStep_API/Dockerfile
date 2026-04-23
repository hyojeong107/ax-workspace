# ─── Stage 1: dependency builder ────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# build-essential은 chromadb/sqlite 컴파일에만 필요 → builder 단계에만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: runtime image ──────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# 보안: non-root 유저 생성
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# builder 스테이지에서 설치된 패키지만 복사 (build-essential 미포함)
COPY --from=builder /install /usr/local

# 앱 소스 복사
COPY app/ ./app/

# ChromaDB 영속 데이터 디렉터리 — 소유권을 appuser에게 부여
RUN mkdir -p /app/data/chroma_db && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# 헬스체크: /health 엔드포인트가 없으면 /docs 로 대체
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 개발용 (코드 수정 시 자동 재시작)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload"]
