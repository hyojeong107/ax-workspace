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
