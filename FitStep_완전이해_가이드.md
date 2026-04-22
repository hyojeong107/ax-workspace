# FitStep 완전 이해 가이드
> 코드를 짜지 않은 사람도 이 앱을 100% 이해할 수 있도록 작성된 문서입니다.

---

## 1. 전체 그림 (5분 만에 이해하기)

### 이 앱이 뭘 하는 앱인가?

FitStep은 **AI 개인 헬스 트레이너 앱**입니다.

사용자가 자신의 정보(나이, 몸무게, 운동 목표 등)와 다니는 헬스장에 있는 기구를 등록하면, AI가 "오늘 이 기구로 이렇게 운동하세요"라고 맞춤 루틴을 짜줍니다. 운동을 마치면 기록을 남기고, 다음 번엔 "지난번보다 무게를 조금 더 올려보세요"라고 점진적으로 성장을 도와줍니다.

---

### 06 / 07 / 08 폴더가 각각 어떤 역할인가?

| 폴더 | 이름 | 역할 | 비유 |
|------|------|------|------|
| `06_FitStep` | CLI 앱 | 터미널(검은 화면)에서 텍스트로 사용하는 초기 버전 | 식당의 "주방 + 계산대"가 하나로 합쳐진 형태 |
| `07_FitStep_Web` | 웹 화면 | 브라우저에서 보이는 예쁜 UI. 버튼·차트·카드 등 | 식당의 "홀(서빙)". 손님이 보는 공간 |
| `08_FitStep_API` | 백엔드 서버 | 데이터를 처리하고 저장하는 보이지 않는 엔진 | 식당의 "주방". 실제 요리가 일어나는 곳 |

> 처음에는 06(CLI)으로 시작해서, 나중에 07(웹 화면) + 08(서버)로 구조를 분리·발전시킨 것입니다.

---

### 세 폴더가 서로 어떻게 연결되는가?

```
사용자 (브라우저)
    ↓ 클릭, 입력
07_FitStep_Web (Streamlit 웹 화면)
    ↓ HTTP 요청 (인터넷으로 데이터 주고받기)
08_FitStep_API (FastAPI 서버)
    ↓ 데이터 저장/조회
  MySQL (회원·루틴·기록 저장)
  ChromaDB (헬스장 기구 정보 저장)
    ↓ 루틴 생성 요청
  OpenAI API (GPT-4o-mini가 운동 루틴 작성)
```

**비유:** 07은 카페 직원(주문 받기), 08은 바리스타(실제 음료 제조), MySQL은 메모장(레시피·주문 기록), ChromaDB는 재료 창고(이 손님이 쓸 수 있는 재료 목록), OpenAI는 요리사(새 레시피 창작)입니다.

> **핵심 한 줄 요약:** 06=CLI 원형, 07=웹 화면, 08=서버. 07이 08에게 요청하고, 08이 DB와 AI를 사용한다.

---

## 2. 데이터 흐름 (사용자 행동 기준)

### 사용자가 로그인하면 내부에서 어떤 일이 벌어지는가?

```
1. 사용자가 아이디/비밀번호 입력 후 "로그인" 클릭
        ↓
2. 07_Web/app.py → api_client.py의 api_login() 함수 호출
        ↓
3. HTTP POST 요청: http://서버주소/db/users/login
        ↓
4. 08_API/db_router.py가 요청 수신
        ↓
5. MySQL의 users 테이블에서 해당 아이디 검색
   비밀번호를 SHA-256으로 변환해서 저장된 값과 비교
   (SHA-256: 비밀번호를 알아볼 수 없는 숫자+문자 조합으로 바꾸는 기법)
        ↓
6. 일치하면 사용자 정보(id, 이름, 목표 등) 반환
        ↓
7. 07_Web이 st.session_state.user_id 에 ID를 저장
   (session_state: 웹 페이지가 바뀌어도 "로그인 상태"를 기억하는 임시 메모장)
        ↓
8. 메인 메뉴 화면으로 이동
```

> **비유:** 도서관 카드로 출입문을 찍으면, 직원이 회원 명부(MySQL)에서 카드 번호를 찾아보고 맞으면 문을 열어주는 것과 같습니다.

---

### 운동 루틴을 추천받을 때 코드가 어떤 순서로 실행되는가?

```
1. 사용자가 "오늘의 루틴 추천받기" 클릭
        ↓
2. app.py → api_client.py → GET /db/routines/today/{user_id}
   "혹시 오늘 루틴 이미 만들어 뒀어?" 먼저 확인 (캐시 확인)
        ↓
   [이미 있으면] 저장된 루틴 그대로 보여주고 끝
   [없으면] 아래 과정 진행
        ↓
3. GET /db/logs/recent-exercises/{user_id}
   최근 7일 운동 기록 가져오기
        ↓
4. GET /db/logs/progression/{user_id}
   각 운동의 "레벨업 여부" 분석
   (3세트 × 11회 이상 달성했으면 → 무게 7.5% 올리기 제안)
        ↓
5. GET /gym/retrieve/{user_id}
   ChromaDB에서 내 헬스장 기구 정보 꺼내오기
        ↓
6. recommender.py가 프롬프트(AI에게 보내는 질문) 조립:
   "나이 25세, 몸무게 70kg, 목표: 근력 증가,
    우리 헬스장엔 바벨 렉·스미스 머신·덤벨만 있어,
    지난주 스쿼트 3세트×12회/50kg 했어, 이번엔 올릴 때 됐어.
    오늘 운동 루틴 JSON 형식으로 짜줘."
        ↓
7. OpenAI GPT-4o-mini가 루틴 JSON 생성
   → 예: [{"name":"스쿼트","sets":3,"reps":10,"weight_kg":53.75}]
        ↓
8. POST /db/routines 로 MySQL에 저장
        ↓
9. 웹 화면에 카드·차트 형태로 표시
```

> **비유:** 주치의가 "이 환자 차트(기록)"와 "이 병원 보유 장비 목록"을 보고 "오늘 이 장비로 이 치료를 하세요"라고 처방전을 쓰는 과정입니다.

---

### 운동 기록을 저장하면 데이터가 어디에 어떻게 저장되는가?

```
1. 사용자가 "스쿼트: 3세트 / 12회 / 55kg / 메모: 허리 조심" 입력
        ↓
2. app.py → api_client.py → POST /db/logs
        ↓
3. 08_API/db_router.py가 MySQL의 workout_logs 테이블에 INSERT:
   user_id=1, routine_id=5, exercise_name="스쿼트",
   sets_done=3, reps_done=12, weight_kg=55, note="허리 조심"
        ↓
4. 모든 운동 완료 후 PATCH /db/routines/{id}/complete
   routines 테이블의 is_completed를 0→1로 변경
        ↓
5. 다음번 루틴 추천 때 이 기록을 참고해서 "이번엔 59kg 도전!" 제안
```

> **비유:** 종이 운동 일지에 오늘 한 운동을 기록하고, 책장에 꽂아두면 다음 번에 트레이너가 그걸 꺼내보고 "지난번보다 올려봅시다"라고 말하는 것과 같습니다.

> **핵심 한 줄 요약:** 사용자 행동 → 웹(07) → 서버(08) → MySQL/ChromaDB 순서로 데이터가 흐르고, OpenAI는 루틴 생성 단계에서만 호출된다.

---

## 3. 핵심 기술 개념 설명

### RAG가 뭔지, 이 프로젝트에서 왜 쓰는가?

**RAG(Retrieval-Augmented Generation)** = "검색 후 생성"

AI에게 질문할 때, 관련 정보를 미리 찾아서 함께 넣어주는 기법입니다.

**문제 상황:** GPT에게 "운동 루틴 짜줘"라고 하면 바벨도 없는데 바벨 운동을 추천할 수 있습니다. GPT는 내 헬스장 기구를 모르니까요.

**RAG 해결법:**
```
1단계 (저장): 내 헬스장 기구 정보를 ChromaDB에 저장
2단계 (검색): 루틴 추천 전에 "이 사람 헬스장 기구" 꺼내오기
3단계 (주입): GPT에게 질문할 때 그 정보를 같이 넣어주기
→ GPT가 "이 사람 헬스장엔 스미스 머신만 있구나" 알고 추천
```

> **비유:** 요리 레시피 AI에게 "오늘 뭐 해먹을까?"라고 물을 때, 먼저 내 냉장고 재료를 사진 찍어서 같이 보여주면 "냉장고에 있는 재료로만" 레시피를 추천하는 것입니다.

---

### ChromaDB가 뭔지, MySQL과 뭐가 다른가?

| | MySQL | ChromaDB |
|---|---|---|
| 저장하는 것 | 표(테이블) 형태의 정형 데이터 | 텍스트의 "의미"를 숫자로 변환한 벡터 |
| 검색 방식 | 정확히 일치하는 것 찾기 | 의미적으로 비슷한 것 찾기 |
| 예시 질문 | "user_id가 1인 사람 찾아줘" | "근력 운동에 좋은 기구 찾아줘" |
| 이 프로젝트 사용 | 회원정보, 루틴, 운동기록 | 헬스장 기구 정보 |

**벡터(Vector)란?** 텍스트를 AI가 이해할 수 있는 숫자 배열로 바꾼 것입니다.
- "바벨 스쿼트 렉" → [0.23, -0.45, 0.87, ...] (1536개의 숫자)
- 의미가 비슷한 문장은 비슷한 숫자 배열이 됩니다.

> **비유:** MySQL은 엑셀 파일(정확한 값 검색), ChromaDB는 "느낌이 비슷한 것" 찾는 추천 시스템(넷플릭스 추천 알고리즘처럼)입니다.

---

### FastAPI가 뭔지, Streamlit과 역할이 어떻게 나뉘는가?

**FastAPI (08폴더)** = 눈에 안 보이는 백엔드 서버
- 데이터를 받아서 MySQL/ChromaDB에 저장하거나 꺼내주는 역할
- 주소 형태: `GET /db/users/1` → "1번 유저 정보 줘"
- 비유: **배달 앱의 주문 처리 시스템** (주문 받아서 주방에 전달)

**Streamlit (07폴더)** = 눈에 보이는 프론트엔드
- 버튼, 차트, 입력 폼 등 화면을 만드는 도구
- 파이썬 코드로 웹 화면을 쉽게 만들 수 있음
- 비유: **식당의 홀과 메뉴판** (손님이 보고 주문하는 공간)

```
Streamlit (화면 담당)  ←→  FastAPI (데이터 처리 담당)
   "버튼 클릭됨"           "DB에서 꺼내서 줄게"
   "결과 화면에 표시"        "AI한테 물어보고 저장할게"
```

> **비유:** Streamlit은 카페 인테리어와 메뉴판, FastAPI는 주문을 받아 처리하는 POS 시스템과 바리스타입니다.

---

### Docker가 왜 필요한가?

**Docker** = 앱을 "컨테이너"라는 작은 상자에 넣어서 어디서든 똑같이 실행되게 만드는 도구

**Docker 없을 때 문제:**
```
개발자 PC: "잘 돌아가는데요?"
서버: "MySQL 버전이 달라서 안 되는데요?"
다른 개발자: "Python 3.11인데 3.9 문법이 있어서 오류나요"
```

**Docker 있을 때:**
```
docker compose up
→ MySQL 8.0 + FastAPI 서버 + ChromaDB 
  모두 동일한 환경으로 한 번에 실행
```

이 프로젝트의 `docker-compose.yml`은 두 가지를 자동 실행합니다:
1. **mysql** 컨테이너 - MySQL 8.0 데이터베이스
2. **gym-rag** 컨테이너 - FastAPI 서버 (포트 3000)

> **비유:** Docker는 "레시피 + 재료 + 조리도구"를 하나의 박스에 넣어서 어느 주방에서 열어도 똑같은 요리가 나오게 만드는 밀키트입니다.

> **핵심 한 줄 요약:** RAG=기구정보 주입 기법, ChromaDB=의미 검색 DB, FastAPI=데이터 처리 서버, Streamlit=화면, Docker=환경 통일 도구.

---

## 4. 파일별 역할 퀵 가이드

### 06_FitStep (CLI 버전)

| 파일 | 한 줄 설명 | 이 기능 고치려면? |
|------|-----------|----------------|
| [main.py](06_FitStep/main.py) | 앱 시작점. "1.루틴추천 2.기록입력 3.대시보드" 메뉴 루프 | 메뉴 항목 추가/변경 시 |
| [db/database.py](06_FitStep/db/database.py) | MySQL 연결하고 테이블 4개 자동 생성 | DB 연결 오류, 테이블 구조 변경 시 |
| [db/user_repo.py](06_FitStep/db/user_repo.py) | 회원가입·로그인·정보수정 SQL 쿼리 모음 | 로그인/회원가입 로직 변경 시 |
| [modules/recommender.py](06_FitStep/modules/recommender.py) | GPT-4o-mini 호출해서 운동 루틴 JSON 생성 | 루틴 추천 방식, 프롬프트 수정 시 |
| [modules/progression.py](06_FitStep/modules/progression.py) | "레벨업 기준"(3세트×11회) 판단 및 무게 7.5% 증가 계산 | 레벨업 기준이나 증가율 바꾸고 싶을 때 |
| [modules/workout_logger.py](06_FitStep/modules/workout_logger.py) | 운동 완료 후 세트/횟수/무게 입력받아 저장 | 기록 입력 항목 추가 시 |
| [modules/dashboard.py](06_FitStep/modules/dashboard.py) | 완료 루틴 수·연속 운동일·운동별 최고기록 표시 | 대시보드 항목 추가/변경 시 |
| [modules/gym_setup.py](06_FitStep/modules/gym_setup.py) | 헬스장 기구 목록 입력받아 JSON 저장 | 기구 등록 화면 수정 시 |
| [rag/gym_rag.py](06_FitStep/rag/gym_rag.py) | 기구 정보 ChromaDB 저장 및 검색 (로컬/API 두 모드) | ChromaDB 저장/검색 방식 바꿀 때 |
| [seed_gym.py](06_FitStep/seed_gym.py) | 헬스장 샘플 데이터를 ChromaDB에 미리 넣어두는 스크립트 | 초기 테스트 데이터 변경 시 |

### 07_FitStep_Web (웹 UI)

| 파일 | 한 줄 설명 | 이 기능 고치려면? |
|------|-----------|----------------|
| [app.py](07_FitStep_Web/app.py) | 전체 웹 화면 (로그인·메뉴·루틴추천·기록·대시보드·기구등록) | 화면 디자인, UI 로직 수정 시 |
| [api_client.py](07_FitStep_Web/api_client.py) | FastAPI 서버에 HTTP 요청 보내는 함수 모음 | API 연결 오류, 새 API 추가 시 |
| [.streamlit/secrets.toml](07_FitStep_Web/.streamlit/secrets.toml) | Streamlit Cloud용 환경변수 (API 주소, 키) | 배포 환경 설정 변경 시 |

### 08_FitStep_API (백엔드 서버)

| 파일 | 한 줄 설명 | 이 기능 고치려면? |
|------|-----------|----------------|
| [app/main.py](08_FitStep_API/app/main.py) | FastAPI 서버 시작점 + /gym/* 엔드포인트 | 헬스장 기구 관련 API 수정 시 |
| [app/db_router.py](08_FitStep_API/app/db_router.py) | /db/* 엔드포인트 전체 (회원·루틴·기록·운동목록) | 데이터 CRUD API 수정 시 |
| [app/db.py](08_FitStep_API/app/db.py) | MySQL 연결 & 테이블 초기화 | DB 연결 설정 변경 시 |
| [app/db_schemas.py](08_FitStep_API/app/db_schemas.py) | 요청/응답 데이터 형식 정의 (UserCreate, LogSave 등) | API 요청/응답 필드 추가할 때 |
| [app/auth.py](08_FitStep_API/app/auth.py) | X-API-Key 헤더로 인증 처리 | API 보안 설정 변경 시 |
| [app/indexing.py](08_FitStep_API/app/indexing.py) | 기구 정보를 임베딩해서 ChromaDB에 저장 | ChromaDB 저장 방식 변경 시 |
| [app/retrieval.py](08_FitStep_API/app/retrieval.py) | ChromaDB에서 기구 정보 꺼내서 텍스트로 변환 | 기구 정보 검색 방식 변경 시 |
| [docker-compose.yml](08_FitStep_API/docker-compose.yml) | MySQL + FastAPI 서버 동시 실행 설정 | Docker 환경 포트·볼륨 변경 시 |

> **핵심 한 줄 요약:** 화면 고치면 app.py, API 고치면 db_router.py, AI 프롬프트 고치면 recommender.py, DB 구조 고치면 database.py/db.py.

---

## 5. 내가 자주 헷갈릴 포인트

### 로컬 모드 vs API 모드 차이

ChromaDB를 사용하는 방법이 두 가지입니다.

**로컬 모드** (`.env`에 `RAG_API_URL` 없을 때)
```
앱 → ChromaDB 파일 직접 읽기/쓰기
경로: 06_FitStep/data/chroma_db/
```
- 장점: 서버 없이 바로 실행 가능
- 단점: CLI 앱(06)에서만 사용 가능. 웹(07)과 공유 불가

**API 모드** (`.env`에 `RAG_API_URL=http://localhost:3000` 있을 때)
```
앱 → FastAPI 서버(08) → ChromaDB
```
- 장점: 웹(07)과 CLI(06) 모두 같은 ChromaDB 공유
- 단점: 08 서버가 먼저 실행되어 있어야 함

> **언제 어떤 모드?** 혼자 테스트할 때는 로컬 모드, 웹 앱으로 배포할 때는 반드시 API 모드.

---

### .env vs secrets.toml - 언제 각각 쓰는가?

| | `.env` | `.streamlit/secrets.toml` |
|---|---|---|
| 위치 | 각 폴더 루트 (06, 07, 08) | `07_FitStep_Web/.streamlit/` |
| 언제 씀 | **내 컴퓨터에서 로컬 개발할 때** | **Streamlit Cloud에 배포할 때** |
| 누가 읽음 | Python의 `dotenv` 라이브러리 | Streamlit 프레임워크 |
| git에 올라가면? | 절대 안 됨 (.gitignore에 있음) | 절대 안 됨 (Cloud 설정창에 입력) |

**실제 동작 방식** (`07_FitStep_Web/app.py` 상단에 이런 코드가 있음):
```python
# 1. 로컬이면 .env 파일에서 읽기
load_dotenv()

# 2. Streamlit Cloud면 secrets.toml에서 읽기
if "RAG_API_URL" in st.secrets:
    os.environ["RAG_API_URL"] = st.secrets["RAG_API_URL"]
```
→ 어떤 환경이든 결국 `os.environ["RAG_API_URL"]`로 통일됩니다.

> **헷갈릴 때 판단법:** 지금 내 컴퓨터에서 실행 중이면 `.env`, 인터넷에 올린 상태면 `secrets.toml`.

---

### ChromaDB 데이터가 실제로 어디에 저장되는가?

**로컬 개발 시:**
```
06_FitStep/data/chroma_db/
├── chroma.sqlite3           ← 메타데이터 (SQLite 파일)
└── ede37fcd-4817-4c6b-.../  ← 실제 벡터 데이터 (바이너리 파일)
    ├── data_level0.bin
    ├── header.bin
    └── length.bin
```

**Docker 배포 시:**
```
Docker 볼륨: chroma_data
→ 실제 경로: /var/lib/docker/volumes/fitstep_chroma_data/_data/
  (서버 컴퓨터 안에 숨겨진 폴더. docker compose down 해도 유지됨)
```

> **주의:** 로컬 모드로 저장한 ChromaDB 데이터는 Docker 컨테이너 안의 ChromaDB와 완전히 별개입니다. 로컬에서 기구를 등록했다고 Docker 환경에서 보이지 않습니다.

---

### Docker를 쓸 때와 안 쓸 때 차이

**Docker 없이 (로컬 개발)**
```bash
# 터미널 1: MySQL 실행 (이미 설치되어 있어야 함)
# 터미널 2: FastAPI 실행
cd 08_FitStep_API && uvicorn app.main:app --port 3000
# 터미널 3: Streamlit 실행
cd 07_FitStep_Web && streamlit run app.py
```
- 직접 Python 환경 설정 필요
- MySQL을 별도로 설치해야 함
- 버전 충돌 발생 가능

**Docker 있을 때 (배포/공유)**
```bash
cd 08_FitStep_API
docker compose up -d
# 끝. MySQL + FastAPI 서버가 한 번에 실행됨
```
- MySQL 설치 불필요
- 환경 설정 자동화
- `docker compose down`으로 한 번에 종료

**언제 Docker가 꼭 필요한가?**
- Streamlit Cloud에 배포해서 다른 사람도 쓰게 할 때
- 내 컴퓨터를 서버로 쓸 때 (ngrok 터널링과 함께)
- 팀원과 동일한 환경 공유할 때

> **핵심 한 줄 요약:** 로컬 모드=빠른 테스트용, API 모드=웹 배포용. .env=내 컴퓨터용, secrets.toml=클라우드용. ChromaDB는 각 환경마다 별도 저장. Docker=환경 패키징 도구.

---

## 참고: 전체 실행 순서 (Streamlit Cloud 배포 기준)

```
1. cd 08_FitStep_API && docker compose up -d
   (MySQL + FastAPI 서버 실행)

2. ngrok http 3000
   (내 컴퓨터를 인터넷에서 접근 가능하게 터널 열기)
   → https://abc123.ngrok.io 같은 주소 생성

3. Streamlit Cloud 설정창에서:
   RAG_API_URL = "https://abc123.ngrok.io"
   RAG_API_KEY = "내가 설정한 키"
   OPENAI_API_KEY = "sk-proj-..."

4. Streamlit Cloud에서 07_FitStep_Web/app.py 배포
   → 누구나 브라우저로 접속 가능
```

---

## 부록: FitStep 프로젝트 원본 분석 문서

> 아래는 프로젝트의 기술적 세부 사항을 담은 원본 분석 문서입니다. 위 설명을 읽고 난 뒤 참고 자료로 활용하세요.

---

# FitStep 프로젝트 전체 분석

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [06_FitStep - CLI 기반 헬스 코치](#06_fitstep---cli-기반-헬스-코치)
3. [07_FitStep_web - Streamlit 웹 인터페이스](#07_fitstep_web---streamlit-웹-인터페이스)
4. [08_FitStep_API - FastAPI 백엔드 서버](#08_fitstep_api---fastapi-백엔드-서버)
5. [시스템 아키텍처](#시스템-아키텍처)
6. [API 연동 방식](#api-연동-방식)
7. [데이터베이스 구조](#데이터베이스-구조)
8. [환경변수 통합 요약](#환경변수-통합-요약)
9. [실행 및 배포 방법](#실행-및-배포-방법)

---

## 프로젝트 개요

**FitStep**은 OpenAI API와 RAG(Retrieval-Augmented Generation) 기술을 활용한 **개인 맞춤형 AI 헬스 코치 애플리케이션**입니다.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 사용자 프로필 등록 | 나이, 키, 몸무게, 체력 수준, 운동 목표(복수), 건강 주의사항 입력 |
| AI 운동 루틴 추천 | OpenAI GPT-4o-mini가 프로필·이력·진행 상태를 분석해 맞춤 루틴 생성 |
| RAG 기반 헬스장 맞춤화 | 사용자의 헬스장 기구 정보를 벡터DB(ChromaDB)에 저장 후 AI가 해당 기구만 추천 |
| 운동 기록 관리 | 실제 수행한 세트·횟수·무게·메모 저장 |
| 점진적 향상 분석 | Progressive Overload 원리에 따라 무게·횟수 증가 자동 제안 |
| 성장 대시보드 | 완료 루틴 수·연속 운동일·운동별 최고 기록 등 시각화 |

### 기술 스택

| 계층 | 기술 |
|------|------|
| CLI | Python 3.9+, Rich (컬러 테이블·패널) |
| 웹 UI | Streamlit, Plotly (차트) |
| 백엔드 API | FastAPI, uvicorn |
| 데이터베이스 | MySQL 8.0 (관계형), ChromaDB 1.5.8 (벡터DB) |
| AI 모델 | OpenAI GPT-4o-mini (루틴 생성), text-embedding-3-small (임베딩) |
| 배포 | Docker Compose, Streamlit Cloud, ngrok (터널링) |

---

## 06_FitStep - CLI 기반 헬스 코치

### 파일 구조

```
06_FitStep/
├── main.py                      # 앱 진입점 - 메인 메뉴 루프
├── seed_gym.py                  # 초기 헬스장 데이터 벡터DB 적재
├── requirements.txt
├── .env                         # 환경변수
│
├── db/
│   ├── database.py              # MySQL 연결 & 테이블 초기화
│   └── user_repo.py             # 사용자 CRUD
│
├── modules/
│   ├── user_setup.py            # 사용자 프로필 입력 & 선택
│   ├── recommender.py           # OpenAI API 호출로 루틴 생성
│   ├── workout_logger.py        # 운동 완료 기록 입력
│   ├── progression.py           # 점진적 향상 분석
│   ├── dashboard.py             # 성장 대시보드 표시
│   └── gym_setup.py             # 헬스장 기구 정보 입력·관리
│
├── rag/
│   ├── __init__.py
│   └── gym_rag.py               # ChromaDB 임베딩 저장·검색 (로컬 또는 API 모드)
│
└── data/
    ├── gym_1.json               # 사용자별 헬스장 기구 정보
    └── chroma_db/               # ChromaDB 벡터 저장소 (로컬 개발용)
```

### 환경변수 (.env)

```env
OPENAI_API_KEY=sk-proj-...

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<password>
DB_NAME=fitstep

# 설정 시 API 모드로 전환 (선택사항)
RAG_API_URL=http://localhost:3000
RAG_API_KEY=<api_key>
```

### 주요 모듈 설명

#### db/database.py - MySQL 연결 & 초기화

```python
def get_connection():
    # charset=utf8mb4로 한글 저장 지원

def init_db():
    # 앱 최초 실행 시 4개 테이블 자동 생성
    # users / routines / workout_logs / exercises
    # 기존 테이블에 username/password_hash 컬럼 없으면 마이그레이션
```

#### db/user_repo.py - 사용자 관리

```python
save_user(name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes, username, password)
    # 새 사용자 생성 & ID 반환 / SHA-256 해시로 비밀번호 저장

get_user_by_login(username, password)
    # 아이디·비밀번호로 사용자 조회

get_user(user_id)
    # ID로 사용자 정보 조회

username_exists(username)
    # 아이디 중복 확인

update_user_weight(user_id, new_weight_kg)
    # 체중 업데이트
```

#### modules/recommender.py - 루틴 추천

1. 오늘 루틴 캐시 확인 → 있으면 재사용
2. 최근 7일 운동 기록에서 점진적 향상 분석
3. ChromaDB에서 사용자 헬스장 기구 정보 검색
4. 프롬프트 구성: 사용자 프로필 + 진행 분석 + 헬스장 기구 정보
5. `gpt-4o-mini`에 JSON 생성 요청
6. 결과를 routines 테이블에 저장

**OpenAI 호출 설정:**
```python
client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"},
    temperature=0.7
)
```

**반환 JSON 형식:**
```json
{
  "exercises": [
    {
      "name": "스미스 머신 스쿼트",
      "category": "하체",
      "sets": 3,
      "reps": 12,
      "weight_kg": 50.0,
      "tip": "렉 대기 시 덤벨로 대체"
    }
  ],
  "advice": "오늘은 스미스 머신으로 스쿼트를 진행합니다..."
}
```

#### modules/progression.py - 점진적 향상 분석

```python
def analyze_progression(user_id, exercise_name) -> dict:
    """
    레벨업 판단 기준:
    ① 기록이 2회 이상
    ② 최근 기록의 세트 수 >= 3
    ③ 평균 반복 수 >= 11회
    → 모두 만족하면 "레벨업 권장"

    제안:
    - 맨몸 운동: 횟수 +2회 또는 더 어려운 변형
    - 기구 운동: 현재 무게 × 1.075 (약 7.5% 증가)
    """

def build_progression_context(user_id, past_exercises) -> str:
    """
    최근 운동들의 진행 분석을 텍스트로 변환해 AI 프롬프트에 주입합니다.

    반환 예시:
    - 스쿼트: 3회 수행 | 최근 3세트×12회 / 50kg | ⬆ 레벨업 권장 | 무게를 53.75kg으로 늘려보세요
    - 벤치프레스: 2회 수행 | 최근 3세트×10회 / 35kg | → 현행 유지
    """
```

#### modules/workout_logger.py - 운동 기록

- 이미 기록된 운동은 자동 건너뛰기 (중간에 앱 종료해도 이어서 가능)
- 각 운동마다 실제 세트 수, 반복 수, 무게, 메모 입력
- 모든 운동 완료 시 `routines.is_completed = 1` 설정

#### modules/dashboard.py - 성장 대시보드

표시 항목:
- 완료한 루틴 수
- 총 운동 기록 수
- 활동한 날 수
- 연속 운동일 수
- 운동별 성장 현황 테이블 (레벨업 권장/유지, 최고 기록, 다음 목표)

#### rag/gym_rag.py - RAG 파이프라인

**2가지 모드:**

| 모드 | 조건 | 설명 |
|------|------|------|
| 로컬 | RAG_API_URL 미설정 | ChromaDB를 로컬 파일시스템에 직접 저장 |
| API | RAG_API_URL 설정 | FastAPI 백엔드로 위임, HTTP REST 통신 |

**주요 함수:**

```python
save_gym_to_vector_db(user_id, gym_data)
    # 헬스장 기구 정보를 임베딩 후 저장
    # 요약 문서 1개 + 기구별 개별 문서 N개

retrieve_gym_context(user_id) -> str
    # 헬스장 정보를 프롬프트용 텍스트로 반환
    # 반환 예시: "헬스장: 우리동네 헬스장\n보유 기구 전체: ..."

has_gym_data(user_id) -> bool
    # 해당 사용자의 헬스장 데이터 존재 여부
```

---

## 07_FitStep_web - Streamlit 웹 인터페이스

### 파일 구조

```
07_FitStep_web/
├── app.py                       # Streamlit 메인 앱 (UI 로직)
├── api_client.py                # FastAPI 백엔드 HTTP 클라이언트
├── requirements.txt
└── .streamlit/
    └── secrets.toml             # Streamlit Secrets (환경변수)
```

### api_client.py - FastAPI 클라이언트

**설정:**
```python
def _base() -> str:
    # RAG_API_URL 우선순위: 환경변수 → st.secrets

def _h() -> dict:
    # X-API-Key 헤더 생성
    # RAG_API_KEY 환경변수 또는 st.secrets에서 읽음
```

**주요 API 호출 함수:**

| 함수 | 메서드 & 경로 | 역할 |
|------|-------------|------|
| `api_save_user()` | POST /db/users | 회원가입 |
| `api_login()` | POST /db/users/login | 로그인 |
| `api_save_routine()` | POST /db/routines | 루틴 저장 |
| `api_get_today_routine()` | GET /db/routines/today/{uid} | 오늘 루틴 조회 |
| `api_save_log()` | POST /db/logs | 운동 기록 저장 |
| `api_get_stats()` | GET /db/logs/stats/{uid} | 종합 통계 |
| `api_get_progression()` | GET /db/logs/progression/{uid} | 운동별 성장현황 |

### app.py - Streamlit 앱 구조

1. **환경 설정**: 로컬 .env 로드 + Streamlit Secrets → 환경변수 자동 주입
2. **디자인**: Black & White 테마 (배경 흰색, 버튼·테두리 검정)
3. **세션 상태 관리**:
   ```python
   st.session_state.page        # 현재 페이지
   st.session_state.user_id     # 로그인한 사용자 ID
   st.session_state.user        # 사용자 정보 딕셔너리
   st.session_state.today_result  # 오늘의 루틴 객체
   ```

**주요 페이지:**

| 페이지 함수 | 내용 |
|-----------|------|
| `page_login()` | 로그인/회원가입 폼 |
| `page_menu()` | 메인 메뉴 (루틴추천/기록/대시보드/기구등록/로그아웃) |
| `page_recommend()` | Plotly 도넛·바 차트 + 운동 카드 + AI 조언 |
| `page_logging()` | 진행 상황 칩 + Progress Bar + 운동별 입력 폼 |
| `page_dashboard()` | 통계 카드 4개 + 30일 히트맵 + 최대중량 바 차트 + 성장 테이블 |
| `page_gym()` | 기구 목록 테이블 + 추가/수정 폼 + ChromaDB 저장 |

### 환경변수

**로컬 (.env):**
```env
RAG_API_URL=http://localhost:3000
RAG_API_KEY=<api_key>
```

**Streamlit Cloud (.streamlit/secrets.toml):**
```toml
RAG_API_URL = "https://ngrok-tunnel-url.ngrok.io"
RAG_API_KEY = "<api_key>"
```

---

## 08_FitStep_API - FastAPI 백엔드 서버

### 파일 구조

```
08_FitStep_API/
├── app/
│   ├── main.py                  # FastAPI 진입점 + /gym/* 엔드포인트
│   ├── db_router.py             # /db/* 엔드포인트 (CRUD)
│   ├── db.py                    # MySQL 연결 & 초기화
│   ├── db_schemas.py            # Pydantic 모델
│   ├── auth.py                  # API Key 인증
│   ├── indexing.py              # ChromaDB 임베딩 저장
│   ├── retrieval.py             # ChromaDB 검색
│   └── __init__.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── DEPLOY.md
```

### app/auth.py - API Key 인증

```python
def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    요청 헤더의 X-API-Key를 환경변수 RAG_API_KEY와 비교합니다.
    RAG_API_KEY 미설정 시 인증 비활성화 모드로 동작합니다.
    """
    expected = os.getenv("RAG_API_KEY")
    if not expected:
        return "no-auth"
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

### app/main.py - /gym/* 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /gym/index | 헬스장 기구 임베딩 후 ChromaDB 저장 |
| GET | /gym/retrieve/{user_id} | 헬스장 정보 프롬프트용 텍스트로 반환 |
| GET | /gym/exists/{user_id} | 헬스장 데이터 존재 여부 |
| GET | /gym/data/{user_id} | 저장된 헬스장 원본 데이터 반환 (Streamlit 폼 복원용) |
| GET | /health | 헬스체크 |

**POST /gym/index 요청 형식:**
```json
{
  "user_id": 1,
  "gym_data": {
    "gym_name": "우리동네 헬스장",
    "equipment": [
      {"name": "바벨 스쿼트 렉", "quantity": 1, "weight_range": "최대 100kg", "notes": ""},
      {"name": "스미스 머신", "quantity": 1, "weight_range": "", "notes": ""}
    ],
    "notes": "오후 6~8시 붐빔"
  }
}
```

### app/db_router.py - /db/* 엔드포인트

#### Users

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /db/users | 회원가입 (username 중복 확인, SHA-256 비밀번호 해싱) |
| POST | /db/users/login | 로그인 |
| GET | /db/users/{id} | 사용자 정보 조회 |
| GET | /db/users | 전체 사용자 목록 |
| PATCH | /db/users/{id}/weight | 체중 업데이트 |

#### Routines

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /db/routines | 루틴 저장 (exercises 테이블 자동 upsert 포함) |
| GET | /db/routines/today/{uid} | 오늘 루틴 조회 |
| PATCH | /db/routines/{id}/complete | 루틴 완료 처리 |
| DELETE | /db/routines/today/{uid} | 오늘 루틴 및 로그 전부 삭제 |

#### Workout Logs

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /db/logs | 운동 기록 저장 |
| GET | /db/logs/recent/{uid} | 최근 기록 조회 (limit 파라미터) |
| GET | /db/logs/recent-exercises/{uid} | 최근 N일 운동 목록 |
| GET | /db/logs/stats/{uid} | 종합 통계 (완료 루틴, 총 기록, 활동일, 연속일) |
| GET | /db/logs/progression/{uid} | 운동별 성장 현황 |
| GET | /db/logs/exercise-history/{uid}/{name} | 특정 운동 이력 |

#### Exercises

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /db/exercises/sync | RapidAPI ExerciseDB에서 1500개 운동 목록 동기화 |
| GET | /db/exercises/list | GPT 프롬프트용 운동 목록 반환 |
| GET | /db/exercises/gif | 운동 GIF URL 조회 (캐싱 포함) |

### app/db_schemas.py - Pydantic 모델

```python
class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    fitness_level: str
    goal: str
    health_notes: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    name: str
    username: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    fitness_level: Optional[str]
    goal: Optional[str]
    health_notes: Optional[str]

class RoutineSave(BaseModel):
    user_id: int
    exercises_json: str  # JSON 문자열
    ai_advice: str

class LogSave(BaseModel):
    user_id: int
    routine_id: int
    exercise_name: str
    sets_done: int
    reps_done: int
    weight_kg: float
    note: Optional[str] = ""

class EquipmentItem(BaseModel):
    name: str
    quantity: Optional[int] = None
    weight_range: Optional[str] = None
    notes: Optional[str] = None

class GymData(BaseModel):
    gym_name: str
    equipment: List[EquipmentItem]
    notes: Optional[str] = None

class IndexRequest(BaseModel):
    user_id: int
    gym_data: GymData
```

### app/indexing.py - ChromaDB 임베딩 저장

```python
def index_gym(user_id: int, gym_data: GymData) -> int:
    """
    저장 구조:
    1. 요약 문서 (1개)
       - 메타데이터: {"user_id": 1, "doc_type": "summary", "gym_json": "..."}
       - 문서: "헬스장: 우리동네 헬스장\n보유 기구 전체: 바벨 스쿼트 렉, ..."

    2. 기구별 개별 문서 (N개)
       - 메타데이터: {"user_id": 1, "doc_type": "equipment", "eq_name": "바벨 스쿼트 렉"}
       - 문서: "기구명: 바벨 스쿼트 렉 / 수량: 1개 / ..."

    동작:
    1. 기존 사용자 데이터 삭제
    2. OpenAI text-embedding-3-small으로 임베딩 생성
    3. ChromaDB에 저장
    """
```

### app/retrieval.py - ChromaDB 검색

```python
def retrieve_context(user_id: int) -> str:
    """
    프롬프트용 텍스트 반환 예시:
    헬스장: 우리동네 헬스장
    보유 기구 전체: 바벨 스쿼트 렉, 스미스 머신, ...
    특이사항: 오후 6~8시 붐빔

    기구명: 바벨 스쿼트 렉 / 수량: 1개 / 무게 범위: 최대 100kg
    ...
    """

def get_gym_data(user_id: int) -> dict | None:
    # summary 메타데이터에서 gym_json 반환 (Streamlit 폼 복원용)

def gym_exists(user_id: int) -> bool:
    # 해당 사용자 헬스장 데이터 존재 여부
```

### docker-compose.yml

```yaml
services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: fitstep
      MYSQL_CHARSET: utf8mb4
    volumes:
      - mysql_data:/var/lib/mysql

  gym-rag:
    build: .
    ports:
      - "3000:3000"
    environment:
      - OPENAI_API_KEY
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=root
      - DB_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - DB_NAME=fitstep
    volumes:
      - chroma_data:/app/data/chroma_db
    depends_on:
      mysql:
        condition: service_healthy
```

---

## 시스템 아키텍처

### 로컬 개발 환경

```
사용자
  ├── CLI 앱 (06_FitStep/main.py)
  │     └── 직접 연결
  └── Streamlit Web (07_FitStep_web/app.py :8501)
        └── HTTP REST (api_client.py)
              │
              ▼
        ┌─────────────────────────────────────┐
        │  MySQL :3306 (DB: fitstep)          │
        │  users / routines / workout_logs    │
        └─────────────────────────────────────┘
        ┌─────────────────────────────────────┐
        │  ChromaDB (data/chroma_db/)         │
        │  컬렉션: gym_equipment              │
        └─────────────────────────────────────┘
        ┌─────────────────────────────────────┐
        │  OpenAI API                         │
        │  gpt-4o-mini / text-embedding-3-small│
        └─────────────────────────────────────┘
```

### Docker 배포 환경 (Streamlit Cloud)

```
Streamlit Cloud (07_FitStep_web)
  └── HTTP REST
        ↓
      ngrok 터널 (로컬 PC)
        ↓
      Docker Compose (08_FitStep_API)
        ├── FastAPI :3000
        │     ├── /gym/* → ChromaDB
        │     └── /db/*  → MySQL
        ├── MySQL :3306
        └── ChromaDB /chroma_db
```

---

## API 연동 방식

### OpenAI API

**사용 모델:**
- `gpt-4o-mini` - 운동 루틴 생성
- `text-embedding-3-small` - 헬스장 기구 임베딩

**클라이언트 초기화:**
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**프롬프트 구성 흐름:**
```
사용자 프로필 (나이/몸무게/목표/주의사항)
  + 최근 7일 운동 이력
  + 점진적 향상 분석 결과
  + ChromaDB에서 검색한 헬스장 기구 정보
          ↓
recommender._build_prompt() → 프롬프트 생성
          ↓
client.chat.completions.create(
    model="gpt-4o-mini",
    response_format={"type": "json_object"},
    temperature=0.7
)
          ↓
json.loads(response) → 운동 목록 & 조언
          ↓
MySQL routines 테이블 저장
```

### FastAPI REST API

**베이스 URL:**
- 로컬: `http://localhost:3000`
- 클라우드: `https://ngrok-uuid.ngrok.io`

**인증 헤더:**
```python
headers = {"X-API-Key": os.getenv("RAG_API_KEY")}
```

### ChromaDB

**임베딩 모델:** `text-embedding-3-small` (OpenAI)
**컬렉션:** `gym_equipment`
**메타데이터 필터:**
```python
collection.get(where={"user_id": {"$eq": user_id}})
```

### RapidAPI ExerciseDB (선택사항)

- `/db/exercises/sync` 엔드포인트로 운동 목록 1500개 동기화
- `/db/exercises/gif` 엔드포인트로 운동 GIF URL 조회 및 DB 캐싱
- 환경변수: `RAPIDAPI_KEY`

---

## 데이터베이스 구조

### MySQL 테이블

#### users

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 고유 ID |
| name | VARCHAR(100) | 사용자명 |
| username | VARCHAR(50) UNIQUE | 로그인 아이디 |
| password_hash | VARCHAR(255) | SHA-256 해시 비밀번호 |
| age | INT | 나이 |
| gender | VARCHAR(10) | male / female / other |
| height_cm | FLOAT | 키 (cm) |
| weight_kg | FLOAT | 몸무게 (kg) |
| fitness_level | VARCHAR(20) | beginner / intermediate / advanced |
| goal | VARCHAR(200) | 운동 목표 (쉼표 구분) |
| health_notes | TEXT | 건강 주의사항 |
| created_at | DATETIME | 등록 일시 |

#### routines

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 고유 ID |
| user_id | INT FK | 사용자 ID |
| routine_date | DATE | 루틴 날짜 (하루 1개) |
| exercises_json | TEXT | 운동 목록 JSON |
| ai_advice | TEXT | AI 조언 메시지 |
| is_completed | TINYINT(1) | 완료 여부 (0/1) |
| created_at | DATETIME | 생성 일시 |

**exercises_json 예시:**
```json
[
  {
    "name": "스미스 머신 스쿼트",
    "category": "하체",
    "sets": 3,
    "reps": 12,
    "weight_kg": 50.0,
    "tip": "렉 대기 시 덤벨로 대체"
  }
]
```

#### workout_logs

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 고유 ID |
| user_id | INT FK | 사용자 ID |
| routine_id | INT FK | 루틴 ID |
| exercise_name | VARCHAR(100) | 운동 이름 |
| sets_done | INT | 실제 수행한 세트 수 |
| reps_done | INT | 실제 수행한 반복 수 |
| weight_kg | FLOAT | 사용한 무게 (맨몸=0) |
| note | TEXT | 메모 |
| logged_at | DATETIME | 기록 일시 |

#### exercises

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 고유 ID |
| name | VARCHAR(100) UNIQUE | 운동 이름 (한글) |
| name_en | VARCHAR(150) | 운동 이름 (영어) |
| category | VARCHAR(50) | 부위 (가슴/등/하체 등) |
| body_part | VARCHAR(50) | 신체 부위 (RapidAPI 기준) |
| gif_url | VARCHAR(512) | 동작 설명 GIF URL |
| synced | TINYINT(1) | RapidAPI 동기화 여부 |
| created_at | DATETIME | 생성 일시 |

### ChromaDB 저장소

**경로:** `data/chroma_db/` (로컬) 또는 Docker 볼륨 `chroma_data`
**컬렉션:** `gym_equipment`

**문서 ID 패턴:**
- 요약 문서: `{user_id}_summary`
- 기구별 문서: `{user_id}_eq_0`, `{user_id}_eq_1`, ...

**메타데이터 필드:**
- `user_id` (int) - 필터링 용도
- `doc_type` (str) - "summary" 또는 "equipment"
- `eq_name` (str) - 기구명 (equipment 타입만)
- `gym_json` (str) - 원본 헬스장 데이터 JSON (summary 타입만)

---

## 환경변수 통합 요약

| 변수 | 예시값 | 용도 | 필수 여부 |
|------|--------|------|----------|
| OPENAI_API_KEY | sk-proj-... | OpenAI API 호출 (루틴 생성 + 임베딩) | 필수 |
| DB_HOST | localhost | MySQL 호스트 | 필수 |
| DB_PORT | 3306 | MySQL 포트 | 필수 |
| DB_USER | root | MySQL 사용자 | 필수 |
| DB_PASSWORD | - | MySQL 비밀번호 | 필수 |
| DB_NAME | fitstep | 데이터베이스명 | 필수 |
| RAG_API_URL | http://localhost:3000 | FastAPI 백엔드 URL | 선택 |
| RAG_API_KEY | - | FastAPI 인증 키 | 선택 (백엔드 사용 시) |
| MYSQL_ROOT_PASSWORD | - | Docker MySQL 초기 비밀번호 | Docker 배포 시 필수 |
| RAPIDAPI_KEY | - | ExerciseDB API 키 (운동 GIF) | 선택 |

---

## 실행 및 배포 방법

### 1. CLI 앱 (06_FitStep)

```bash
cd 06_FitStep
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env 파일 작성 (환경변수 섹션 참고)

python3 seed_gym.py  # 헬스장 데이터 초기 적재 (선택)
python3 main.py
```

### 2. Docker 배포 (08_FitStep_API)

```bash
cd 08_FitStep_API

# .env 파일 작성
# OPENAI_API_KEY, MYSQL_ROOT_PASSWORD, RAG_API_KEY

docker compose up -d --build

# 헬스체크
curl http://localhost:3000/health
```

### 3. Streamlit 로컬 실행 (07_FitStep_web)

```bash
cd 07_FitStep_web
pip install -r requirements.txt

# .env 또는 .streamlit/secrets.toml에 RAG_API_URL, RAG_API_KEY 설정

streamlit run app.py
# 브라우저: http://localhost:8501
```

### 4. Streamlit Cloud 배포

1. 로컬 PC에서 ngrok 터널 실행: `ngrok http 3000`
2. Docker 백엔드 실행: `docker compose up -d`
3. Streamlit Cloud (https://share.streamlit.io)에서 GitHub 저장소 연결
4. 메인 파일: `07_FitStep_web/app.py`
5. Secrets 설정:
   ```toml
   RAG_API_URL = "https://ngrok-uuid.ngrok.io"
   RAG_API_KEY = "<api_key>"
   OPENAI_API_KEY = "sk-proj-..."
   ```

### 모듈 간 의존 관계

```
06_FitStep (CLI)
  ├── db/ (MySQL 직접 연결)
  ├── modules/ (기능 모듈)
  ├── rag/gym_rag.py (로컬 ChromaDB 또는 API 모드)
  └── OpenAI API (gpt-4o-mini, text-embedding-3-small)

07_FitStep_web (Streamlit)
  ├── 06_FitStep/rag/gym_rag.py (RAG 모듈 import)
  ├── api_client.py → 08_FitStep_API (HTTP REST)
  └── OpenAI API (rag 모듈 경유)

08_FitStep_API (FastAPI)
  ├── MySQL (CRUD)
  ├── ChromaDB (벡터 저장소)
  └── OpenAI API (임베딩)
```
