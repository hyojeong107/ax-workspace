# FitStep Docker 개발환경 가이드
> Mac과 Windows 어디서나 동일하게 실행되는 개발환경 세팅

---

## 도커 쓰면 뭐가 달라지는가?

### 지금 (도커 없이)
```
Mac에서 작업할 때:
  - Python venv 따로 만들기
  - MySQL 설치 + 설정
  - .env 파일 따로 관리
  - 패키지 따로 설치
  - 실행 명령어 여러 개

Windows에서 작업할 때:
  - 위 과정 전부 다시
  - venv 경로도 달라서 충돌
```

### 도커 사용 후
```
Mac에서 작업할 때:    docker compose up  → 끝
Windows에서 작업할 때: docker compose up  → 끝

환경 설정, 패키지, DB 전부 자동. 코드만 수정하면 됨.
```

---

## DB는 어떻게 되는건가?

도커 안에 MySQL 컨테이너가 돌아가고, 데이터는 **볼륨**에 따로 저장돼요.

```
[Docker 컨테이너들]
  ├── mysql 컨테이너  ←→  mysql_data 볼륨 (데이터 영구 보존)
  └── FastAPI 컨테이너

컨테이너를 껐다 켜도 데이터는 볼륨에 남아있음
"docker compose down -v" 할 때만 데이터 날아감 (주의!)
```

Mac MySQL 따로 설치 안 해도 됨. 도커가 MySQL을 대신 실행해줌.

---

## 코드 수정은 어떻게 하는가?

핵심은 **볼륨 마운트**예요.

```
내 컴퓨터 (실제 파일)          컨테이너 (실행 환경)
08_FitStep_API/app/  ←→  컨테이너 안의 /app/
       ↑                         ↑
  VSCode로 수정             이 파일을 읽어서 실행 중

→ 내 컴퓨터에서 파일 수정 = 컨테이너가 바로 변경사항 감지 → 자동 재시작
```

즉, **VSCode에서 코드 수정하면 바로 반영**돼요. 도커 재시작 필요 없어요.

---

## 전체 구조 그림

```
내 컴퓨터
│
├── [Docker]
│     ├── MySQL 컨테이너 (포트 3306)  ← DB 역할
│     └── FastAPI 컨테이너 (포트 8000) ← API 서버
│           ↕ 볼륨 마운트
│     08_FitStep_API/app/ (내 코드)
│
├── [터미널] streamlit run app.py
│     → 브라우저: http://localhost:8501
│
└── [브라우저] localhost:8501
      → Streamlit 웹 화면
      → 버튼 클릭 → localhost:8000으로 API 호출
      → FastAPI → MySQL 조회 → 응답
```

Streamlit(07 폴더)은 도커 밖에서 실행해요. API(08 폴더)와 DB만 도커 안에 있어요.

---

## 사전 준비

### Docker Desktop 설치

**Mac:**
1. https://www.docker.com/products/docker-desktop/ 에서 "Download for Mac" 클릭
2. Apple Silicon(M1/M2/M3)이면 "Mac with Apple chip" 선택
3. `.dmg` 파일 열어서 설치
4. 설치 후 Docker Desktop 앱 실행 (상단 메뉴바에 고래 아이콘 뜨면 성공)

**Windows:**
1. 같은 사이트에서 "Download for Windows" 클릭
2. 설치 중 "Use WSL 2" 옵션 체크 (권장)
3. 설치 후 Docker Desktop 실행

**설치 확인:**
```bash
docker --version
# Docker version 24.x.x 같은 버전 번호 나오면 성공
```

---

## 처음 세팅하기 (Mac / Windows 동일)

### 1단계: 코드 받기

```bash
git clone [레포 주소]
cd ax-workspace
```
> 이미 있으면 `git pull` 만

### 2단계: .env 파일 만들기

`08_FitStep_API` 폴더 안에 `.env` 파일 생성:

```bash
# Mac
cd ~/ax-workspace/08_FitStep_API

# Windows
cd C:\Users\user\Desktop\dev\ax-workspace\ax-workspace\08_FitStep_API
```

`.env` 파일 내용 (`.env.example` 참고해서 실제 값으로 채우기):
```
OPENAI_API_KEY=sk-proj-여기에실제키입력
RAG_API_KEY=여기에_비밀번호_입력
MYSQL_ROOT_PASSWORD=여기에_비밀번호_입력
DB_HOST=mysql
DB_PORT=3306
DB_USER=root
DB_PASSWORD=여기에_비밀번호_입력
DB_NAME=fitstep
RAPIDAPI_KEY=여기에실제키입력
```

> `DB_HOST=mysql` ← 이게 중요! 로컬 개발과 달리 도커에선 `mysql` 이라고 써야 함
> (도커 네트워크 안에서 컨테이너 이름으로 서로를 찾음)

### 3단계: docker-compose.yml 수정 (코드 수정 반영되게)

`08_FitStep_API/docker-compose.yml` 에서 `gym-rag` 서비스에 볼륨 마운트 추가:

> 현재 파일에서 `gym-rag` 서비스 아래 `volumes:` 항목을 찾아 아래와 같이 수정:

```yaml
  gym-rag:
    build: .
    container_name: gym_rag_api
    ports:
      - "8000:8000"          # ← 포트를 8000으로 변경 (기존 3000에서)
    environment:
      - OPENAI_API_KEY
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=root
      - DB_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - DB_NAME=fitstep
      - RAG_API_KEY=${RAG_API_KEY}
      - RAPIDAPI_KEY=${RAPIDAPI_KEY}
    env_file:
      - .env
    volumes:
      - chroma_data:/app/data/chroma_db
      - ./app:/app/app          # ← 이 줄 추가! 코드 수정이 바로 반영됨
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped
```

### 4단계: Dockerfile CMD 수정 (개발용 --reload 추가)

`08_FitStep_API/Dockerfile` 맨 아래 CMD 줄 수정:

```dockerfile
# 개발용 (코드 수정 시 자동 재시작)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--reload"]
```

### 5단계: 07_FitStep_Web .env 확인

`07_FitStep_Web/.env` 파일에 API URL이 8000으로 되어 있는지 확인:

```
RAG_API_URL=http://localhost:8000
RAG_API_KEY=여기에_비밀번호_입력
```

### 6단계: 실행!

**터미널 1 - API + DB 실행:**
```bash
cd ax-workspace/08_FitStep_API
docker compose up --build
```

처음엔 이미지 빌드해서 3~5분 걸려요. 이후엔 빠름.

아래 메시지 나오면 성공:
```
fitstep_mysql  | ready for connections
gym_rag_api    | Application startup complete.
```

**터미널 2 - 웹 실행 (Mac):**
```bash
cd ax-workspace/07_FitStep_Web
source venv/bin/activate
streamlit run app.py
```

**터미널 2 - 웹 실행 (Windows):**
```bash
cd ax-workspace\07_FitStep_Web
venv\Scripts\activate
streamlit run app.py
```

**브라우저에서 http://localhost:8501 접속**

---

## 매번 작업할 때 실행 순서

```
터미널 1: docker compose up          (API + DB)
터미널 2: streamlit run app.py       (웹)
브라우저: http://localhost:8501
```

종료할 때:
```
터미널 2: Ctrl+C
터미널 1: Ctrl+C  또는  docker compose down
```

> `docker compose down -v` 는 DB 데이터까지 삭제되니 주의!

---

## Mac ↔ Windows 작업 전환할 때

```bash
# 작업 끝날 때
git add .
git commit -m "작업 내용"
git push

# 다른 PC에서
git pull
docker compose up      # (08_FitStep_API 폴더에서)
streamlit run app.py   # (07_FitStep_Web 폴더에서)
```

DB 데이터는 각 PC의 도커 볼륨에 따로 저장돼요.
Mac DB와 Windows DB는 공유되지 않아요. 코드만 git으로 공유됨.

---

## 자주 쓰는 도커 명령어

```bash
# 실행 중인 컨테이너 확인
docker ps

# 로그 보기 (에러 확인할 때)
docker logs gym_rag_api
docker logs fitstep_mysql

# MySQL 직접 접속
docker exec -it fitstep_mysql mysql -u root -p fitstep

# 코드 말고 Dockerfile이나 requirements.txt 바꿨을 때 (이미지 재빌드)
docker compose up --build

# 컨테이너 중지
docker compose down

# 컨테이너 + DB 데이터까지 전부 삭제 (주의!)
docker compose down -v
```

---

## 처음 실행 시 DB 초기화 (운동 목록 동기화)

컨테이너 실행 후 새 터미널에서 한 번만 실행:

```bash
curl -X POST "http://localhost:8000/db/exercises/sync" -H "X-API-Key: 여기에_비밀번호_입력"
```

`{"synced": 1300}` 응답 오면 성공. 30초 정도 걸려요.

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| `Cannot connect to Docker daemon` | Docker Desktop 안 켜짐 | Docker Desktop 앱 실행 |
| `Port 8000 already in use` | 기존 uvicorn이 실행 중 | `lsof -i:8000` 으로 프로세스 찾아서 종료 |
| `Connection refused localhost:8000` | 컨테이너 아직 시작 중 | 30초 기다렸다가 다시 시도 |
| DB 데이터가 없음 | 처음 실행이라 sync 안 함 | exercises sync curl 명령어 실행 |
| 코드 수정이 반영 안 됨 | 볼륨 마운트 설정 안 됨 | 3단계 docker-compose.yml 수정 확인 |
