# 🚀 FitStep 배포 가이드

Streamlit Cloud(웹 UI) + Docker(FastAPI + MySQL + ChromaDB) + ngrok(터널) 조합으로 배포합니다.

---

## 아키텍처 개요

```
[사용자 브라우저]
      │
      ▼
[Streamlit Cloud]  ← GitHub 자동 배포
  07_Streamlit/07-1.Streamlit.py
      │  HTTP REST (RAG_API_URL)
      ▼
[ngrok HTTP 터널]  ← 포트 8000 하나만 사용
      │
      ▼
[로컬 PC — Docker Compose]
  ┌─────────────────────────────┐
  │  gym_rag_api (FastAPI)      │  :8000
  │  - /gym/* → ChromaDB RAG   │
  │  - /db/*  → MySQL CRUD     │
  ├─────────────────────────────┤
  │  fitstep_mysql (MySQL 8.0)  │  내부 전용
  ├─────────────────────────────┤
  │  Volume: chroma_data        │  ChromaDB 영속화
  │  Volume: mysql_data         │  MySQL 영속화
  └─────────────────────────────┘
```

**핵심 원칙**
- Streamlit Cloud는 MySQL에 직접 접근하지 않음 — 모든 DB 작업은 FastAPI REST API 경유
- ngrok 터널 1개(HTTP, 포트 8000)로 FastAPI 전체 노출
- `OPENAI_API_KEY`는 OS 환경 변수에서만 가져옴 (`.env`에 저장하지 않음)

---

## 1단계 — 로컬 PC: Docker 실행

### 사전 준비

- Docker Desktop 설치 및 실행
- `08_Advanced_RAG/.env` 파일에 아래 내용 입력 (이미 작성됨):

```env
RAG_API_KEY=khj570832!
MYSQL_ROOT_PASSWORD=khj570832!
```

- `OPENAI_API_KEY`는 OS 시스템 환경 변수에 설정 (Windows: 시스템 속성 → 환경 변수)

### Docker 실행

```bash
cd ax-workspace/08_Advanced_RAG

# 최초 실행 or 코드 변경 후
docker compose down
docker compose up -d --build

# 상태 확인 (fitstep_mysql + gym_rag_api 둘 다 Up 이어야 함)
docker ps

# 로그 확인
docker logs gym_rag_api
```

### 동작 확인

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

## 2단계 — ngrok 터널 실행

### ngrok 설치 및 인증 (최초 1회)

```bash
# https://ngrok.com 에서 계정 생성 후 authtoken 복사
ngrok config add-authtoken <your-token>
```

### 터널 실행

```bash
ngrok http 8000
```

터미널에 표시되는 URL 복사:
```
Forwarding  https://xxxx-xxx-xxx.ngrok-free.app -> http://localhost:8000
```

> ngrok을 재시작하면 URL이 바뀝니다. 바뀔 때마다 Streamlit Cloud Secrets의 `RAG_API_URL`을 업데이트해야 합니다.

---

## 3단계 — GitHub Push

```bash
cd ax-workspace

git add 07_Streamlit/ 08_Advanced_RAG/
git commit -m "deploy: FastAPI middleware + Streamlit Cloud setup"
git push origin main
```

---

## 4단계 — Streamlit Cloud 배포

### 배포 설정

1. [share.streamlit.io](https://share.streamlit.io) 접속 → GitHub 로그인
2. **New app** 클릭
3. 설정:
   - Repository: `<your-repo>`
   - Branch: `main`
   - Main file path: `07_Streamlit/07-1.Streamlit.py`

### Secrets 설정

Streamlit Cloud 앱 설정 → **Secrets** 탭에 아래 내용 입력:

```toml
RAG_API_URL = "https://xxxx-xxx-xxx.ngrok-free.app"
RAG_API_KEY = "khj570832!"
OPENAI_API_KEY = "sk-..."
```

> `RAG_API_URL`은 ngrok 터널 URL로 교체하세요.

---

## 5단계 — requirements.txt (Streamlit Cloud용)

`07_Streamlit/requirements.txt` 파일이 있어야 Streamlit Cloud가 패키지를 설치합니다:

```
streamlit
openai>=2.0.0
plotly
pandas
requests
chromadb==1.5.8
```

---

## 운영 주의사항

| 상황 | 조치 |
|------|------|
| ngrok 재시작 시 URL 변경됨 | Streamlit Cloud Secrets의 `RAG_API_URL` 업데이트 |
| PC 재부팅 후 | `docker compose up -d` + `ngrok http 8000` 재실행 |
| 데이터 유실 없음 | MySQL·ChromaDB 데이터는 Docker Volume에 영속화됨 |
| FastAPI 로그 확인 | `docker logs -f gym_rag_api` |
| MySQL 접속 | `docker exec -it fitstep_mysql mysql -u root -pkhj570832! fitstep` |

---

## 환경 변수 전체 목록

| 변수 | 위치 | 설명 |
|------|------|------|
| `OPENAI_API_KEY` | OS 환경 변수 + Streamlit Secrets | OpenAI API 키 |
| `RAG_API_KEY` | `08_Advanced_RAG/.env` + Streamlit Secrets | FastAPI 인증 키 |
| `RAG_API_URL` | Streamlit Secrets | ngrok URL (로컬에서는 불필요) |
| `MYSQL_ROOT_PASSWORD` | `08_Advanced_RAG/.env` | MySQL root 비밀번호 |
| `DB_HOST` | docker-compose.yml 내 고정 | `mysql` (Docker 내부 서비스명) |
