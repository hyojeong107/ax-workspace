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

# 앱 소스 + 공공데이터 인덱싱 스크립트 복사
COPY app/ ./app/
COPY init_public_data.py ./
COPY ["data/국민연령별추천운동정보.csv", "data/체력측정 및 운동처방 종합 데이터.json", "./data/"]
COPY entrypoint.sh ./

# ChromaDB 영속 데이터 디렉터리 — 소유권을 appuser에게 부여
RUN mkdir -p /app/data/chroma_db \
    && chown -R appuser:appgroup /app \
    && chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
