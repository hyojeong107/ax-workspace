# FitStep 프로젝트 전체 분석

## 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [06_FitStep - CLI 기반 헬스 코치](#06_fitstep---cli-기반-헬스-코치)
3. [07_FitStep_web - Streamlit 웹 인터페이스](#07_fitstep_web---streamlit-웹-인터페이스)
4. [08_FitStep_API - FastAPI 백엔드 서버](#08_fitstep_api---fastapi-백엔드-서버)
5. [09_SingleAgent - ReAct 단일 에이전트](#09_singleagent---react-단일-에이전트)
6. [10_MultiAgent - 멀티에이전트 파이프라인](#10_multiagent---멀티에이전트-파이프라인)
7. [시스템 아키텍처](#시스템-아키텍처)
8. [API 연동 방식](#api-연동-방식)
9. [데이터베이스 구조](#데이터베이스-구조)
10. [환경변수 통합 요약](#환경변수-통합-요약)
11. [실행 및 배포 방법](#실행-및-배포-방법)

---

## 프로젝트 개요

**FitStep**은 OpenAI API와 RAG(Retrieval-Augmented Generation) 기술을 활용한 **개인 맞춤형 AI 헬스 코치 애플리케이션**입니다.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 사용자 프로필 등록/수정 | 나이, 키, 몸무게, 체력 수준, 운동 목표(복수), 건강 주의사항, 부상 태그 입력·수정 |
| AI 운동 루틴 추천 | OpenAI GPT-4o-mini가 프로필·이력·진행 상태를 분석해 맞춤 루틴 생성 |
| RAG 기반 헬스장 맞춤화 | 사용자의 헬스장 기구 정보를 벡터DB(ChromaDB)에 저장 후 AI가 해당 기구만 추천 |
| 공공데이터 기반 맞춤화 | 국민체육공단 체력측정(950건) + 운동추천 데이터를 RAG로 활용해 연령/BMI/성별 기반 루틴 근거 제공 |
| 컨디션 기반 루틴 개인화 | 루틴 추천 전 오늘의 컨디션(1-5점)·근육통 부위 입력 → AI가 볼륨·제외 부위 자동 조정 |
| 운동 split 자동 감지 | 최근 2일 운동 기록을 분석해 이미 훈련한 부위를 제외하고 루틴 생성 |
| 쿨다운 기반 순환 추천 | 운동별 마지막 수행일을 추적해 부위별 회복 기간(2~3일) 동안 제외, 오래 쉰 운동 우선 추천 |
| 운동 기록 관리 | 실제 수행한 세트·횟수·무게·메모 저장 |
| 점진적 향상 분석 | Progressive Overload 원리에 따라 무게·횟수 증가 자동 제안 |
| 성장 대시보드 | 완료 루틴 수·연속 운동일·운동별 최고 기록 등 시각화 |
| 체력 수준 승급 제안 | 완료 루틴 10회 이상 + 레벨업 운동 3가지 이상 시 자동으로 fitness_level 올리기 배너 표시 |

### 기술 스택

| 계층 | 기술 |
|------|------|
| CLI | Python 3.9+, Rich (컬러 테이블·패널) |
| 웹 UI | Streamlit, Plotly (차트) |
| 백엔드 API | FastAPI, uvicorn |
| 데이터베이스 | MySQL 8.0 (관계형), ChromaDB 1.5.8 (벡터DB) |
| AI 모델 | OpenAI GPT-4o-mini (루틴 생성), text-embedding-3-small (임베딩) |
| RAG 프레임워크 | LangChain (langchain-openai, langchain-chroma) |
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

> **현재 RAG 사용 방식 주의:** `retrieve_gym_context()`는 내부적으로 `collection.get(where={"user_id": ...})`를 사용합니다. 이는 유사도 검색(similarity search)이 아닌 **필터 조회**로, 해당 사용자의 모든 문서를 통째로 반환합니다. 즉, 현재는 ChromaDB를 단순 저장소로 사용하고 있으며, 진정한 의미의 RAG(관련 문서만 선택적 주입)는 아직 구현되지 않은 상태입니다.

### RAG 고도화 계획 (향후 구현 예정)

**방법 1 — 운동 지식 DB RAG** *(구현 예정)*

수백 개의 운동 가이드 문서(부위별, 부상 금기사항, 목표별 적합도)를 ChromaDB에 저장하고, 사용자의 프로필 정보로 유사도 검색을 수행해 가장 관련성 높은 가이드만 GPT 프롬프트에 주입하는 방식.

**현재 방식 vs 개선 방식 비교:**

| | 현재 | 방법 1 구현 후 |
|---|---|---|
| ChromaDB 저장 데이터 | 사용자 헬스장 기구 정보 | 운동 지식 문서 수백 건 (부위별·부상별·목표별 가이드) |
| 검색 방식 | `collection.get()` (전체 조회) | `collection.query(query_embeddings=...)` (유사도 검색) |
| 검색 쿼리 | 없음 (user_id 필터만) | 사용자 부상 태그 + 목표 + 오늘 훈련 부위 조합 |
| GPT 주입 내용 | 기구 목록 전체 | 상위 N개 관련 운동 가이드만 선택적 주입 |

**구현 계획:**
```python
# 1단계: 운동 지식 문서 사전 적재 (seed 스크립트)
#   - 예: "어깨 회전근개 부상 시 금기 운동: 오버헤드 프레스, 업라이트 로우..."
#   - 예: "초급자 하체 루틴: 스쿼트 3×12, 레그프레스 3×15..."

# 2단계: 쿼리 텍스트 생성
query = f"부상: {injury_tags}, 목표: {goal}, 오늘 훈련 부위: {target_body_part}"

# 3단계: 유사도 검색으로 관련 가이드 Top-5 추출
results = collection.query(
    query_embeddings=[embed(query)],
    n_results=5,
    where={"type": "exercise_guide"}
)

# 4단계: GPT 프롬프트에 선택적 주입
# → 부상 금기·목표별 가이드만 포함해 hallucination 감소
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
| `api_update_profile()` | PATCH /db/users/{id}/profile | 프로필 부분 수정 (injury_tags 포함) |
| `api_save_routine()` | POST /db/routines | 루틴 저장 |
| `api_get_today_routine()` | GET /db/routines/today/{uid} | 오늘 루틴 조회 |
| `api_save_log()` | POST /db/logs | 운동 기록 저장 |
| `api_get_stats()` | GET /db/logs/stats/{uid} | 종합 통계 |
| `api_get_progression()` | GET /db/logs/progression/{uid} | 운동별 성장현황 |
| `api_get_rag_context()` | POST /rag/context | 공공데이터 RAG 컨텍스트 조회 (GPT 호출 없음) |

### app.py - Streamlit 앱 구조

1. **환경 설정**: 로컬 .env 로드 + Streamlit Secrets → 환경변수 자동 주입
2. **디자인**: Black & White 테마 (배경 흰색, 버튼·테두리 검정)
3. **세션 상태 관리**:
   ```python
   st.session_state.page           # 현재 페이지
   st.session_state.user_id        # 로그인한 사용자 ID
   st.session_state.user           # 사용자 정보 딕셔너리
   st.session_state.today_result   # 오늘의 루틴 객체
   st.session_state[f"condition_{date.today()}"]  # 오늘의 컨디션 정보 (날짜키 → 다음날 자동 만료)
   ```

**주요 페이지:**

| 페이지 함수 | 내용 |
|-----------|------|
| `page_login()` | 로그인/회원가입 폼 |
| `page_menu()` | 메인 메뉴 (루틴추천/기록/대시보드/기구등록/프로필수정/로그아웃) |
| `page_recommend()` | 컨디션 입력 → 체력수준 승급 배너 → Plotly 도넛·바 차트 + 운동 카드 + AI 조언 |
| `page_logging()` | 진행 상황 칩 + Progress Bar + 운동별 입력 폼 |
| `page_dashboard()` | 통계 카드 4개 + 30일 히트맵 + 최대중량 바 차트 + 성장 테이블 |
| `page_gym()` | 기구 목록 테이블 + 추가/수정 폼 + ChromaDB 저장 |
| `page_profile_edit()` | 체중·키·나이·체력수준·목표·부상태그·건강주의사항 수정 폼 |

**주요 헬퍼 함수:**

| 함수 | 역할 |
|------|------|
| `_build_routine_prompt()` | GPT 프롬프트 생성 (부상·컨디션·split·볼륨가이드라인·공공데이터 RAG·쿨다운 순환 섹션 포함) |
| `recommend_routine()` | BMI 등급·연령대 자동 계산 → `/rag/context` 호출 → 쿨다운 정보 수집 → 프롬프트에 컨텍스트 주입 |
| `_get_recent_body_parts(user_id)` | 최근 2일 운동 로그를 regex로 분석해 훈련한 신체 부위 목록 반환 |
| `_get_exercise_cooldown_info(user_id)` | 운동별 마지막 수행일·경과일수·쿨다운 기준·가용 여부 반환 (progression API 재사용) |
| `_build_cooldown_section(cooldown_info)` | 오늘 수행·쿨다운 중·재추천 가능 3분류로 GPT 프롬프트 섹션 생성 |
| `_check_level_up_suggestion(user, uid)` | 완료 루틴 ≥10 + 레벨업 운동 ≥3 충족 시 승급 배너 표시 |
| `_calc_progression_suggestion()` | 나이·BMI·성별·체력 수준을 고려한 점진적 증가 제안 계산 |

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
| PATCH | /db/users/{id}/profile | 프로필 전체 업데이트 (injury_tags 포함, 보낸 필드만 변경) |

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
| GET | /db/exercises/gif | 운동 GIF URL 조회 (RapidAPI 다운로드 → 로컬 캐싱) |
| POST | /rag/context | 공공데이터 RAG 컨텍스트 반환 (체력측정 유사사례 + 운동추천, GPT 호출 없음) |

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
    injury_tags: Optional[str] = None   # 부상/통증 태그 (쉼표 구분)

class UserProfileUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    health_notes: Optional[str] = None
    injury_tags: Optional[str] = None   # None인 필드는 UPDATE 제외

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

### app/indexing.py - ChromaDB 임베딩 저장 (LangChain 기반)

> 2026-04-24 LangChain으로 전환: `OpenAI SDK 직접 호출` → `OpenAIEmbeddings + Chroma`

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
    2. LangChain OpenAIEmbeddings (text-embedding-3-small)으로 임베딩 생성
    3. LangChain Chroma.add_documents()로 저장
    """
```

### init_public_data.py - 공공데이터 초기 인덱싱 (Phase 0)

> 2026-04-24 신규 추가. 최초 1회 또는 --force 옵션으로 재인덱싱.

**ChromaDB 컬렉션 구조 (전체)**
```
chroma_db/
├── gym_equipment           # 사용자별 헬스장 기구 (user_id 메타데이터 필터)
├── fitness_measurement     # 국민체육공단 체력측정 공공데이터 (950건)
└── exercise_recommendation # 국민체육공단 운동추천 공공데이터 (조합별 묶음)
```

**인덱싱 전략**
| 컬렉션 | 문서 단위 | 주요 메타데이터 |
|---|---|---|
| gym_equipment | 요약 1개 + 기구별 N개 | user_id, doc_type, gym_json |
| fitness_measurement | 1레코드 → 자연어 문장 1개 | source, age_group, gender, grade, bmi, bmi_category, age |
| exercise_recommendation | 조합(연령+BMI+성별+상장+단계) → 1문서 | source, age_group, gender, bmi_grade, award_grade, exercise_step |

**실행**
```bash
# 최초 인덱싱 (데이터 있으면 스킵)
..\venv\Scripts\python init_public_data.py

# 강제 재인덱싱
..\venv\Scripts\python init_public_data.py --force
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

## 09_SingleAgent - ReAct 단일 에이전트

### 개요

08_FitStep_API의 고정 파이프라인을 OpenAI tool-calling 기반 ReAct 에이전트로 재설계한 버전.
GPT가 어떤 도구를 언제 호출할지 스스로 판단하는 구조.

### 파일 구조

```
09_SingleAgent/
├── app/
│   ├── agent.py      # OpenAI tool-calling ReAct 루프 (MAX_ITERATIONS=10)
│   ├── tools.py      # 도구 정의 + 실행 (search_rag, search_web, generate_curriculum, validate_curriculum)
│   ├── main.py       # FastAPI (/health, /auth/login, /auth/verify, /chat)
│   ├── auth.py       # JWT 인증 — 08의 MySQL users 테이블 연동
│   ├── schemas.py    # Pydantic 모델
│   ├── db.py         # MySQL 연결 (08과 동일 스키마)
│   ├── indexing.py   # ChromaDB 스토어 초기화
│   └── retrieval.py  # Hybrid Search (Vector + BM25 + RRF + Reranker)
├── prompts/
│   └── agent_system.txt  # 에이전트 시스템 프롬프트
├── streamlit_app/    # 대화형 Streamlit 프론트엔드
├── Dockerfile
└── docker-compose.yml
```

### 에이전트 도구 4가지

| 도구 | GPT 사용 | 역할 |
|------|---------|------|
| `search_rag` | 없음 | ChromaDB 하이브리드 검색 (체력측정 사례 + 운동추천) |
| `search_web` | 없음 | Tavily 외부 웹 검색 (부상/질환 특수 조건 시) |
| `generate_curriculum` | 있음 (gpt-4o-mini) | 주간 운동 커리큘럼 JSON 생성 |
| `validate_curriculum` | 없음 | 시간/일수/근육 그룹 규칙 검증 (순수 Python) |

### 도커 실행 방법

```bash
# 08을 먼저 실행 (MySQL + ChromaDB 공유)
cd 08_FitStep_API && docker-compose up -d

# 09를 08 네트워크/볼륨에 합류
cd ../09_SingleAgent && docker-compose up -d

# 또는 로컬 실행
cd 09_SingleAgent
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**포트:** API 8001, Streamlit 8502

### 싱글 에이전트 한계

현재 구조에서 싱글 에이전트는 충분하지만, 다음 확장이 필요해지면 멀티에이전트가 정당화됨:
- 병렬 정보 수집 (RAG + 웹 동시 검색)
- 전문화된 도메인 분리 (근력/유산소/재활)
- 커리큘럼 생성 외 다른 목적 에이전트 추가

---

## 10_MultiAgent - 멀티에이전트 파이프라인

### 개요

09_SingleAgent를 기반으로 전문가 에이전트 팀 + 비GPT 에이전트를 결합한 멀티에이전트 시스템.
**핵심 원칙:** 신뢰가 필요한 작업(필터링/검증/계산)은 코드가, 자연어 생성만 GPT가 담당.

### 파일 구조

```
10_MultiAgent/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py     # 파이프라인 메인 컨트롤러 (결정적 흐름)
│   │   ├── specialists.py      # 근력/유산소/재활 전문 에이전트 (각 GPT 1회)
│   │   └── integration.py      # 통합 에이전트 (GPT 1회, 검증 실패 시 재시도)
│   ├── tools/
│   │   ├── exercise_matcher.py # 기구→운동 매핑 (Python 딕셔너리, GPT 없음)
│   │   ├── validator.py        # 커리큘럼 검증 + check_summary (Python, GPT 없음)
│   │   ├── rag_search.py       # ChromaDB 검색 래퍼
│   │   └── web_search.py       # Tavily 검색 래퍼
│   ├── main.py                 # FastAPI + curricula 저장/목록/다운로드 API
│   ├── schemas.py              # ChatResponse에 matched_exercises, specialists_called, pipeline_log 추가
│   ├── db.py                   # curricula 테이블 추가 (기존 스키마 변경 없음)
│   └── auth.py                 # JWT 인증 (09와 동일)
├── prompts/                    # 에이전트 시스템 프롬프트 외부 파일 관리
│   ├── orchestrator.txt        # 전문가 결정 판단 기준
│   ├── strength_agent.txt      # 근력 트레이닝 전문가
│   ├── cardio_agent.txt        # 유산소/심폐 전문가 + 심박수 존
│   ├── rehab_agent.txt         # 재활/물리치료 전문가 + 부상별 가이드
│   └── integration_agent.txt  # 통합 규칙 + 출력 JSON 형식
├── streamlit_app/
│   ├── app.py                  # 개선된 UI (파이프라인 로그, 전문가 태그, 검증 실패 경고)
│   └── api_client.py           # curricula 이력 API 포함
├── eval/
│   ├── code_checks.py          # 코드 검증 항목 (Precision@K, 규칙 통과율 등, GPT 없음)
│   ├── llm_judge.py            # LLM 판단 항목 (Faithfulness, 멀티에이전트 Coherence)
│   └── run_eval.py             # 통합 평가 (코드 검증 + LLM 판단 분리 실행)
├── Dockerfile
└── docker-compose.yml
```

### 파이프라인 흐름

```
사용자 메시지 + 프로필 + gym_data
  ↓
Step 1. match_exercises(equipment)          Python 딕셔너리 매핑 — GPT 없음
  ↓ available_exercises (기구별 운동 목록)
Step 2. search_rag(profile)                 ChromaDB 하이브리드 검색 — GPT 없음
  ↓ rag_context
Step 3. search_web(query)                   Tavily — 부상/질환 있을 때만
  ↓ web_context
Step 4. _analyze_specialists(message, profile)   GPT 1회 — 전문가 결정
  ↓ {"strength": T, "cardio": T, "rehab": T}
Step 5a. run_strength_agent(profile, rag, exercises)  GPT 1회
Step 5b. run_cardio_agent(profile, rag, exercises)    GPT 1회 + 심박수 존 계산
Step 5c. run_rehab_agent(profile, web)               GPT 1회 → forbidden_exercises
  ↓ 각 전문가 세션 JSON
Step 6. run_integration_agent(strength, cardio, rehab)  GPT 1회
  ↓ combined curriculum JSON
Step 7. validate_curriculum(curriculum)              Python 규칙 검증 — GPT 없음
  → 실패 시 Step 6 재시도 (최대 2회, 오류 메시지 전달)
  ↓
curricula 테이블 자동 저장 (검증 통과 시)
```

### 에이전트별 역할

| 에이전트 | GPT | 역할 | 출력 |
|---------|-----|------|------|
| Orchestrator | 1회 | 전문가 필요 여부 결정 | `{strength, cardio, rehab}` |
| Strength Agent | 1회 | 근력 세션 설계 (점진적 과부하, 근육 분할) | sessions JSON |
| Cardio Agent | 1회 | 유산소 세션 + 심박수 존 계산 | sessions + heart_rate_zone |
| Rehab Agent | 1회 | 금지 운동 + 안전 가이드라인 | `{forbidden_exercises, safety_notes}` |
| Integration Agent | 1회 | 전문가 결과 통합, 충돌 방지 | 최종 curriculum JSON |

### 신규 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/chat` | 멀티에이전트 파이프라인 실행 |
| POST | `/curricula/save` | 커리큘럼 수동 저장 |
| GET | `/curricula` | 사용자 커리큘럼 목록 조회 |
| GET | `/curricula/{id}/download` | 커리큘럼 JSON 파일 다운로드 |
| DELETE | `/curricula/{id}` | 커리큘럼 삭제 |

### 미완성 — 다음 세션 구현 예정

주간 커리큘럼 → 오늘의 운동 연결 레이어:

```
POST /curricula/{id}/activate
  → weekly_plan을 날짜별로 분해 → routines 테이블 INSERT

GET /today
  → 오늘 날짜 기준 routines 조회 → 오늘의 운동 반환

Streamlit 요일 탭 UI
  [월] [화] [수] [목] [금] [토] [일]
  → 오늘 탭 자동 포커스 + 운동 카드 + 완료 체크
```

### 도커 실행

```bash
cd 10_MultiAgent
cp .env.example .env   # OPENAI_API_KEY, DB 정보 등 설정
docker-compose up -d   # API: 8001포트, Streamlit: 8502포트
```

**포트:** API 8001, Streamlit 8502 (08/09와 충돌 없음)

---

## 시스템 아키텍처

### 전체 프로젝트 진화 흐름

```
06_FitStep (CLI)          07_FitStep_web (Streamlit)
     │                           │
     └──────────────────────────┤
                                 ▼
                     08_FitStep_API (FastAPI + RAG)
                         MySQL + ChromaDB
                                 │
                                 ├── 09_SingleAgent (ReAct 단일 에이전트)
                                 │       └── 08 MySQL/ChromaDB 공유
                                 │
                                 └── 10_MultiAgent (멀티에이전트 파이프라인)
                                         └── 08 MySQL/ChromaDB 공유
                                             + curricula 테이블 추가
```

### 로컬 개발 환경

```
사용자
  ├── CLI 앱 (06_FitStep/main.py)
  │     └── MySQL 직접 연결
  ├── Streamlit Web (07_FitStep_web :8501)
  │     └── HTTP → 08_FitStep_API :3000
  ├── Single Agent UI (09_SingleAgent/streamlit_app :8502)
  │     └── HTTP → 09_SingleAgent/app :8001
  └── Multi Agent UI (10_MultiAgent/streamlit_app :8502)
        └── HTTP → 10_MultiAgent/app :8001

공유 인프라:
  MySQL :3306  →  users / routines / workout_logs / exercises / curricula
  ChromaDB     →  gym_equipment / fitness_measurement / exercise_recommendation
  OpenAI API   →  gpt-4o-mini / gpt-4o / text-embedding-3-small
```

### Docker 배포 환경

```
08_FitStep_API docker-compose:
  fitstep_mysql      :3307  →  MySQL 8.0
  gym_rag_api        :8000  →  FastAPI (RAG + DB CRUD)
  fitstep_streamlit  :8501  →  07_FitStep_web

09_SingleAgent docker-compose:
  fitstep_single_api :8001  →  FastAPI (Agent)
  fitstep_single_st  :8502  →  Streamlit
  (08의 MySQL/ChromaDB 네트워크/볼륨 공유)

10_MultiAgent docker-compose:
  fitstep_multi_api  :8001  →  FastAPI (Multi-Agent)
  fitstep_multi_st   :8502  →  Streamlit
  fitstep_mysql      :3307  →  MySQL (독립 또는 08 공유)
```

---

## API 연동 방식

### OpenAI API

**사용 모델:**

| 모델 | 용도 | 사용 위치 |
|------|------|---------|
| `gpt-4o-mini` | 운동 루틴 생성, 커리큘럼 생성 | 06~10 전체 |
| `gpt-4o` | 싱글 에이전트 ReAct 루프 | 09_SingleAgent |
| `text-embedding-3-small` | 헬스장 기구 임베딩 | 08_FitStep_API |

**클라이언트 초기화:**
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**루틴 추천 흐름 (07_FitStep_web 기준):**
```
1. page_recommend() 진입
        ↓
2. 오늘 컨디션 미입력 → 컨디션 입력 화면 표시
   (컨디션 점수 1-5 슬라이더 + 근육통 부위 멀티셀렉트)
   → st.session_state["condition_{오늘날짜}"] 에 저장 (다음날 자동 만료)
        ↓
3. _check_level_up_suggestion() 호출
   → 완료 루틴 ≥ 10 AND 레벨업 운동 ≥ 3 이면 st.info 배너 표시
        ↓
4. _get_recent_body_parts(user_id) 호출
   → 최근 2일 workout_logs에서 운동명을 regex로 분석해 훈련 부위 추출
        ↓
4-1. _get_exercise_cooldown_info(user_id) 호출
   → progression API 재사용 → 운동별 마지막 수행일 기준 쿨다운 가용 여부 계산
        ↓
5. _build_routine_prompt() 호출 (condition_info + recent_body_parts + cooldown_info 전달)
   프롬프트에 포함되는 섹션:
   - [사용자 프로필] 나이·몸무게·체력수준·목표
   - [부상 주의사항] injury_tags 기반 금지 운동·대체 운동 안내
   - [오늘 볼륨 조정] 컨디션 점수에 따른 세트 수·강도 조정 지시
   - [오늘 제외할 부위] 근육통 선택 부위 + 최근 2일 훈련 부위 합산
   - [볼륨 가이드라인] goal 기반 세트·반복 수·강도 기준 제시
   - [점진적 향상] progression API 분석 결과
   - [운동 순환 스케줄] 쿨다운 기반 오늘 제외/우선추천/재추천 가능 운동 목록
   - [헬스장 기구] ChromaDB RAG 컨텍스트
        ↓
6. OpenAI GPT-4o-mini → 루틴 JSON 생성
        ↓
7. POST /db/routines → MySQL 저장
        ↓
8. 웹 화면에 카드·차트 표시
```

**멀티에이전트 흐름 (10_MultiAgent 기준):**
```
POST /chat
  ↓
Orchestrator
  ├── match_exercises()      Python 딕셔너리 → 기구별 운동 목록 (GPT 없음)
  ├── search_rag()           ChromaDB → 체력측정/운동추천 컨텍스트 (GPT 없음)
  ├── search_web()           Tavily → 부상/질환 관련 정보 (조건부)
  ├── _analyze_specialists() GPT-4o-mini 1회 → 전문가 결정
  ├── run_strength_agent()   GPT-4o-mini 1회 → 근력 세션 JSON
  ├── run_cardio_agent()     GPT-4o-mini 1회 → 유산소 세션 + 심박수 존
  ├── run_rehab_agent()      GPT-4o-mini 1회 → 금지 운동 + 안전 가이드
  ├── run_integration_agent() GPT-4o-mini 1회 → 통합 커리큘럼 JSON
  └── validate_curriculum()  Python 규칙 → 검증 (실패 시 통합 재시도 최대 2회)
  ↓
curricula 테이블 자동 저장 (검증 통과 시)
```

### FastAPI REST API

**베이스 URL 및 인증 방식 비교:**

| 서버 | URL | 인증 방식 |
|------|-----|---------|
| 08_FitStep_API | `http://localhost:3000` | X-API-Key 헤더 |
| 09_SingleAgent | `http://localhost:8001` | JWT Bearer 토큰 |
| 10_MultiAgent | `http://localhost:8001` | JWT Bearer 토큰 |

### ChromaDB

**임베딩 모델:** `text-embedding-3-small` (OpenAI)

**컬렉션 전체 구성:**

| 컬렉션 | 데이터 | 검색 방식 |
|--------|--------|---------|
| `gym_equipment` | 사용자별 헬스장 기구 | user_id 필터 조회 |
| `fitness_measurement` | 국민체육공단 체력측정 950건 | 벡터 + BM25 + RRF + Reranker |
| `exercise_recommendation` | 연령/BMI/성별별 운동추천 | 벡터 + BM25 + RRF + Reranker |

**Hybrid Search 파이프라인 (09/10 공통):**
```
쿼리
  ├── Vector Search (ChromaDB, Top-10)
  └── BM25 Search (kiwipiepy 형태소 분석, Top-10)
        ↓ RRF 융합 (Reciprocal Rank Fusion)
        ↓ Reranker (ms-marco-MiniLM-L-12-v2, flashrank)
        ↓ 최종 Top-3 반환
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
| injury_tags | VARCHAR(200) | 부상/통증 태그 (쉼표 구분, 예: "무릎,허리") |
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

#### curricula (10_MultiAgent 신규 추가)

멀티에이전트가 생성한 **주간 커리큘럼**을 저장하는 테이블.
기존 `routines`(날짜별 오늘의 운동)와 역할이 다름.

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | 고유 ID |
| user_id | INT FK → users.id | 사용자 ID |
| label | VARCHAR(200) | 커리큘럼 이름 (선택, 예: "4주차 감량 플랜") |
| curriculum_json | LONGTEXT | 주간 커리큘럼 전체 JSON |
| specialists_used | VARCHAR(100) | 참여 전문가 목록 (예: "strength,cardio,rehab") |
| total_days | INT | 주당 운동 일수 |
| is_valid | TINYINT(1) | 코드 검증 통과 여부 |
| validation_json | TEXT | 검증 결과 상세 JSON |
| created_at | DATETIME | 생성 일시 |

**인덱스:**
```sql
CREATE INDEX idx_curricula_user ON curricula(user_id, created_at);
```

**curricula → routines 연결 (다음 세션 구현 예정):**
```
curricula.weekly_plan[0] → routines (오늘~N일 후 날짜별 INSERT)
curricula.weekly_plan[1] → routines
...
→ GET /today 로 오늘 날짜 routines 조회 → 오늘의 운동 표시
```

### DB 테이블 역할 정리

| 테이블 | 역할 | 생성 주체 |
|--------|------|---------|
| `users` | 사용자 프로필 (공통) | 06~10 전체 |
| `routines` | 날짜별 오늘의 운동 (1일 1개) | 06~08, 10(예정) |
| `workout_logs` | 실제 수행 기록 (세트/횟수/무게) | 06~08 |
| `exercises` | 운동 마스터 목록 + GIF | 08 |
| `curricula` | 멀티에이전트 주간 커리큘럼 저장 | 10_MultiAgent |

### ChromaDB 저장소

**Docker 볼륨 구성:**
| 볼륨 | 마운트 경로 | 용도 |
|------|------------|------|
| `chroma_data` | `/app/data/chroma_db` | ChromaDB 벡터 저장소 |
| `mysql_data` | `/var/lib/mysql` | MySQL 데이터 |
| `gifs_data` | `/app/app/static/gifs` | RapidAPI 다운로드 GIF 캐시 (재빌드 후에도 유지) |

**ChromaDB 경로:** `data/chroma_db/` (로컬) 또는 Docker 볼륨 `chroma_data`  
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

### 공통

| 변수 | 예시값 | 용도 | 필수 여부 |
|------|--------|------|----------|
| OPENAI_API_KEY | sk-proj-... | OpenAI API (루틴 생성 + 임베딩 + 에이전트) | 필수 |
| DB_HOST | localhost | MySQL 호스트 | 필수 |
| DB_PORT | 3306 | MySQL 포트 | 필수 |
| DB_USER | root | MySQL 사용자 | 필수 |
| DB_PASSWORD | - | MySQL 비밀번호 | 필수 |
| DB_NAME | fitstep | 데이터베이스명 | 필수 |
| MYSQL_ROOT_PASSWORD | - | Docker MySQL 초기 비밀번호 | Docker 배포 시 필수 |

### 08_FitStep_API 전용

| 변수 | 예시값 | 용도 | 필수 여부 |
|------|--------|------|----------|
| RAG_API_KEY | - | FastAPI X-API-Key 인증 | 선택 (미설정 시 인증 비활성화) |
| ANTHROPIC_API_KEY | - | Claude Haiku (공공데이터 Contextual Retrieval) | 인덱싱 시 필수 |
| RAPIDAPI_KEY | - | ExerciseDB API (운동 GIF 동기화) | 선택 |

### 07_FitStep_web 전용

| 변수 | 예시값 | 용도 | 필수 여부 |
|------|--------|------|----------|
| RAG_API_URL | http://localhost:3000 | 08_FitStep_API 주소 | 필수 |
| RAG_API_KEY | - | 08 API 인증 키 | 선택 |

### 09_SingleAgent / 10_MultiAgent 공통

| 변수 | 예시값 | 용도 | 필수 여부 |
|------|--------|------|----------|
| JWT_SECRET_KEY | change-me | JWT 토큰 서명 키 | 필수 |
| TAVILY_API_KEY | tvly-... | 웹 검색 (부상/질환 특수 조건) | 선택 (없으면 웹 검색 건너뜀) |
| AGENT_API_URL | http://localhost:8001 | Streamlit → FastAPI 주소 | Streamlit 실행 시 필수 |

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
