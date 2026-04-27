# FitStep 배포 가이드

Streamlit을 실행하는 방법은 두 가지입니다.

| 방식 | 언제 쓰나 | FastAPI 백엔드 |
|------|-----------|---------------|
| **로컬 직접 실행** | 개발·테스트 중 빠르게 확인하고 싶을 때 | Docker로 로컬에서 띄움 |
| **Streamlit Cloud 배포** | 외부에 공개하거나 팀원과 공유할 때 | ngrok으로 터널링 |

김효정ㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴㄴ

## 서버 실행 명령어 (개발용)

> Docker Desktop이 실행 중인 상태여야 합니다.

### Windows (PowerShell / CMD)

```powershell
# 1. API 디렉토리 이동
cd C:\Users\user\Desktop\dev\ax-workspace\ax-workspace\08_FitStep_API

# 2. 최초 실행 or 코드 변경 후 — 이미지 재빌드 + 실행
docker compose up -d --build

# 3. 상태 확인 (fitstep_mysql, gym_rag_api 둘 다 Up 이어야 함)
docker ps

# 4. API 정상 확인
curl http://localhost:8000/health

# 5. Streamlit 웹 실행 (별도 터미널)
cd C:\Users\user\Desktop\dev\ax-workspace\ax-workspace\07_FitStep_Web
streamlit run app.py
```

### Mac / Linux (Terminal)

```bash
# 1. API 디렉토리 이동
cd ~/Desktop/dev/ax-workspace/ax-workspace/08_FitStep_API

# 2. 최초 실행 or 코드 변경 후 — 이미지 재빌드 + 실행
docker compose up -d --build

# 3. 상태 확인
docker ps

# 4. API 정상 확인
curl http://localhost:8000/health

# 5. Streamlit 웹 실행 (별도 터미널)
cd ~/Desktop/dev/ax-workspace/ax-workspace/07_FitStep_Web
streamlit run app.py
```

### 자주 쓰는 Docker 명령어

| 상황 | 명령어 |
|------|--------|
| 코드 수정 후 반영 | `docker compose up -d --build gym-rag` |
| MySQL은 유지하고 API만 재시작 | `docker compose restart gym-rag` |
| 로그 확인 | `docker compose logs -f gym-rag` |
| 전체 중지 (데이터 유지) | `docker compose down` |
| 전체 중지 + 볼륨 삭제 (DB 초기화) | `docker compose down -v` |

> **주의:** `down -v`는 MySQL 데이터도 삭제됩니다.

### 포트 정보

| 서비스 | 주소 |
|--------|------|
| FastAPI (Swagger) | http://localhost:8000/docs |
| FastAPI (헬스체크) | http://localhost:8000/health |
| Streamlit 웹 | http://localhost:8501 |

---

## 방법 1 — 로컬에서 Streamlit 직접 실행 (개발용)

### 전체 흐름

```
[브라우저 localhost:8501]
      │
      ▼
[Streamlit 로컬 프로세스]  ← python 직접 실행
      │  HTTP REST
      ▼
[Docker: gym_rag_api]  :8000  ← FastAPI + ChromaDB
[Docker: fitstep_mysql]       ← MySQL
```

### 1. FastAPI 백엔드 Docker 실행

```bash
cd 08_FitStep_API

docker compose up -d --build

# 확인
docker ps  # gym_rag_api, fitstep_mysql 둘 다 Up 이어야 함
curl http://localhost:8000/health
```

### 2. Streamlit 환경 변수 설정

`07_FitStep_Web/.streamlit/secrets.toml` 파일을 아래와 같이 수정합니다.
(이 파일은 `.gitignore`에 등록되어 있으므로 실제 값을 입력해도 됩니다)

```toml
RAG_API_URL = "http://localhost:8000"
RAG_API_KEY = "여기에_비밀번호_입력"
```

> `secrets.toml`은 Streamlit이 자동으로 읽습니다. 별도 `.env` 파일 불필요.

### 3. 의존성 설치 (최초 1회)

```bash
cd 07_FitStep_Web

pip install -r requirements.txt
```

### 4. Streamlit 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속.

### 종료

```bash
# Streamlit: 터미널에서 Ctrl+C
# Docker 백엔드:
docker compose -f ../08_FitStep_API/docker-compose.yml down
```

---

## 방법 2 — Streamlit Cloud 배포 (외부 공개용)

Streamlit Cloud(웹 UI) + Docker(FastAPI + MySQL + ChromaDB) + ngrok(터널) 조합으로 배포합니다.

---

### 아키텍처 개요

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
  │  gym_rag_api (FastAPI)      │  :3000
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
- ngrok 터널 1개(HTTP, 포트 3000)로 FastAPI 전체 노출
- `OPENAI_API_KEY`는 OS 환경 변수에서만 가져옴 (`.env`에 저장하지 않음)

---

## 포트 구성

FastAPI 컨테이너는 포트 **8000**을 사용합니다. 포트 설정은 3곳이 항상 일치해야 합니다.

| 파일 | 설정 위치 | 현재 값 |
|------|-----------|---------|
| `Dockerfile` | `EXPOSE` + `--port` | `8000` |
| `docker-compose.yml` | `ports: "호스트:컨테이너"` | `"8000:8000"` |
| ngrok 터널 | `ngrok http <포트>` | `8000` |

**포트를 바꾸고 싶다면** 위 3곳을 동일한 번호로 수정하면 됩니다.

`docker-compose.yml`의 `ports` 앞뒤 숫자 의미:
- **앞 (호스트 포트)** — 내 PC에서 `localhost:8000`으로 접근할 때 쓰는 포트. 다른 프로세스와 충돌하지 않으면 자유롭게 변경 가능
- **뒤 (컨테이너 포트)** — 컨테이너 내부 uvicorn이 실제로 열고 있는 포트. `Dockerfile`의 `EXPOSE` 및 `--port`와 반드시 일치해야 함

---

## 1단계 — 로컬 PC: Docker 실행

### 사전 준비

- Docker Desktop 설치 및 실행
- `08_Advanced_RAG/.env` 파일에 아래 내용 입력 (이미 작성됨):

```env
RAG_API_KEY=여기에_비밀번호_입력
MYSQL_ROOT_PASSWORD=여기에_비밀번호_입력
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
RAG_API_KEY = "여기에_비밀번호_입력"
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
| PC 재부팅 후 | `docker compose up -d` + `ngrok http 8000` 재실행 (포트 8000 고정) |
| 데이터 유실 없음 | MySQL·ChromaDB 데이터는 Docker Volume에 영속화됨 |
| FastAPI 로그 확인 | `docker logs -f gym_rag_api` |
| MySQL 접속 | `docker exec -it fitstep_mysql mysql -u root -p여기에_비밀번호_입력 fitstep` |

---

## 환경 변수 전체 목록

| 변수 | 위치 | 설명 |
|------|------|------|
| `OPENAI_API_KEY` | OS 환경 변수 + Streamlit Secrets | OpenAI API 키 |
| `RAG_API_KEY` | `08_Advanced_RAG/.env` + Streamlit Secrets | FastAPI 인증 키 |
| `RAG_API_URL` | Streamlit Secrets | ngrok URL (로컬에서는 불필요) |
| `MYSQL_ROOT_PASSWORD` | `08_Advanced_RAG/.env` | MySQL root 비밀번호 |
| `DB_HOST` | docker-compose.yml 내 고정 | `mysql` (Docker 내부 서비스명) |
