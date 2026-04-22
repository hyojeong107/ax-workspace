# FitStep 프로젝트 완전 이해 가이드
> 비전공자도 남에게 설명할 수 있게 — 06 / 07 / 08 프로젝트 한 번에 정리

---

## 목차
1. [이 프로젝트가 뭐하는 건가요?](#1-이-프로젝트가-뭐하는-건가요)
2. [세 프로젝트의 역할 나누기](#2-세-프로젝트의-역할-나누기)
3. [전체 구조 — 물이 흐르는 방향](#3-전체-구조--물이-흐르는-방향)
4. [06_FitStep — CLI 앱 (터미널 버전)](#4-06_fitstep--cli-앱-터미널-버전)
5. [07_FitStep_Web — 웹 화면 (Streamlit)](#5-07_fitstep_web--웹-화면-streamlit)
6. [08_FitStep_API — 백엔드 서버 (FastAPI)](#6-08_fitstep_api--백엔드-서버-fastapi)
7. [데이터베이스 — 어디에 뭘 저장하나](#7-데이터베이스--어디에-뭘-저장하나)
8. [AI가 루틴을 만드는 원리 (RAG)](#8-ai가-루틴을-만드는-원리-rag)
9. [Docker — 왜 쓰고 어떻게 돌아가나](#9-docker--왜-쓰고-어떻게-돌아가나)
10. [Ngrok — 외부에서 접속하게 해주는 터널](#10-ngrok--외부에서-접속하게-해주는-터널)
11. [Streamlit — 화면을 만드는 방식](#11-streamlit--화면을-만드는-방식)
12. [전체 배포 흐름 한 눈에](#12-전체-배포-흐름-한-눈에)
13. [HTTP 메서드 — GET/POST/PATCH/DELETE 차이](#13-http-메서드--getpostpatchdelete-차이)
14. [실제 데이터가 어떻게 생겼나 — JSON 예시](#14-실제-데이터가-어떻게-생겼나--json-예시)
15. [왜 이렇게 만들었나 — 설계 의도 Q&A](#15-왜-이렇게-만들었나--설계-의도-qa)
16. [에러가 났을 때 어디를 보나 — 트러블슈팅](#16-에러가-났을-때-어디를-보나--트러블슈팅)
17. [자주 쓰는 용어 사전](#17-자주-쓰는-용어-사전)

---

## 1. 이 프로젝트가 뭐하는 건가요?

**FitStep**은 AI가 내 헬스장 기구, 체력 수준, 목표에 맞게 **오늘 운동 루틴을 짜줘**는 앱입니다.

핵심 기능을 한 줄씩 정리하면:

| 기능 | 설명 |
|------|------|
| 루틴 추천 | GPT가 내 정보를 보고 오늘 할 운동 4~6개를 JSON으로 뽑아줌 |
| 운동 기록 | 세트 수 / 반복 수 / 무게를 기록해서 DB에 저장 |
| 점진적 과부하 분석 | "이 운동, 이제 무게 올려도 돼요" 자동 판단 |
| 성장 대시보드 | 운동한 날 수, 연속 운동일, 무게 추이 그래프 |
| 헬스장 기구 등록 | 내 헬스장에 있는 기구만 루틴에 넣도록 GPT에 알려줌 |

---

## 2. 세 프로젝트의 역할 나누기

레스토랑에 비유하면 이해가 쉽습니다.

```
06_FitStep        → 직접 주방에서 음식 만들고 먹는 것 (혼자 쓰는 CLI 앱)
07_FitStep_Web    → 손님이 앉아있는 홀 (웹 화면, 브라우저에서 보이는 부분)
08_FitStep_API    → 주방 + 창고 (데이터 저장·조회·AI 처리를 담당하는 서버)
```

| 프로젝트 | 역할 | 사용 기술 | 접속 방법 |
|---------|------|----------|----------|
| 06_FitStep | 터미널에서 직접 실행하는 독립 앱 | Python, Rich | `python main.py` |
| 07_FitStep_Web | 브라우저 웹 화면 | Streamlit | `http://localhost:8501` |
| 08_FitStep_API | 모든 데이터를 처리하는 서버 | FastAPI, Docker | `http://localhost:3000` |

> **중요**: 07은 혼자서 아무것도 못 합니다. 반드시 08이 켜져 있어야 작동합니다.

---

## 3. 전체 구조 — 물이 흐르는 방향

```
[사용자 브라우저]
       ↓  클릭 / 입력
[07_FitStep_Web — Streamlit 웹앱 :8501]
       ↓  "루틴 줘", "기록 저장해줘" — HTTP 요청
[08_FitStep_API — FastAPI 서버 :3000]
       ↓             ↓              ↓
   [MySQL DB]   [ChromaDB]    [OpenAI API]
   (사용자/기록) (헬스장기구   (루틴 생성
                 벡터 저장소)  AI 모델)
```

**한 번의 "루틴 생성" 클릭에 일어나는 일:**

1. 브라우저에서 "루틴 생성" 버튼 클릭
2. Streamlit(07)이 FastAPI(08)에 `POST /db/routines` 요청 전송
3. FastAPI가 MySQL에서 사용자 정보 + 최근 운동 기록 조회
4. FastAPI가 ChromaDB에서 "이 사람 헬스장 기구" 정보 검색
5. 이 모든 정보를 합쳐서 OpenAI GPT에 프롬프트 전송
6. GPT가 운동 목록 JSON으로 응답
7. FastAPI가 MySQL에 저장 후 Streamlit에 결과 반환
8. 화면에 운동 카드로 표시

---

## 4. 06_FitStep — CLI 앱 (터미널 버전)

### 어떤 앱인가?

터미널(까만 창)에서 `python main.py` 실행하면 메뉴가 뜨고, 키보드로 조작하는 앱입니다.  
07/08과 **완전히 독립적**으로 동작하며, 로컬 MySQL에 직접 연결합니다.

### 폴더 구조

```
06_FitStep/
├── main.py              ← 프로그램 시작점. 메뉴 루프
├── seed_gym.py          ← 헬스장 기구 JSON을 ChromaDB에 한 번에 넣어주는 도구
├── requirements.txt     ← 필요한 라이브러리 목록
│
├── modules/             ← 기능별로 나눈 Python 파일들
│   ├── user_setup.py    ← 사용자 정보 입력/조회
│   ├── recommender.py   ← GPT에 루틴 요청하는 로직
│   ├── workout_logger.py← 운동 완료 기록 입력
│   ├── progression.py   ← "무게 올려도 돼" 판단
│   ├── dashboard.py     ← 통계 출력
│   └── gym_setup.py     ← 헬스장 기구 등록
│
├── rag/
│   └── gym_rag.py       ← ChromaDB 저장/검색 담당
│
├── db/
│   ├── database.py      ← MySQL 연결 및 테이블 자동 생성
│   └── user_repo.py     ← 사용자 데이터 CRUD (저장/조회/수정/삭제)
│
└── streamlit_app/       ← 06의 웹버전 (선택 사용, 07과 별개)
    ├── app.py
    └── pages/
```

### 핵심 로직: 루틴은 어떻게 만들어지나?

```
[recommender.py 동작 순서]

1. MySQL에서 최근 7일 운동 목록 가져오기
2. progression.py로 "어떤 운동을 얼마나 했는지" 분석
3. ChromaDB에서 "이 사람 헬스장 기구" 텍스트 가져오기
4. 아래 내용을 하나의 프롬프트로 조립:
   - 사용자 나이/키/체중/체력수준/목표
   - 최근에 한 운동들
   - 헬스장에 있는 기구 목록
   - "JSON 형식으로 반환해" 지시
5. OpenAI GPT-4o-mini에 전송
6. 응답 파싱 → DB 저장
```

### 점진적 과부하 판단 기준

```
조건 1: 같은 운동을 2회 이상 한 기록이 있다
조건 2: 최근 세션에서 3세트 이상 했다
조건 3: 평균 반복 횟수가 11회 이상이다

→ 세 조건 모두 충족 → "무게를 7.5% 올려도 됩니다" 알림
```

---

## 5. 07_FitStep_Web — 웹 화면 (Streamlit)

### 어떤 역할인가?

사용자가 보는 **브라우저 화면** 전체를 담당합니다.  
실제 데이터 처리는 하지 않고, "08 서버에 요청 → 결과 화면에 표시"만 합니다.

### 폴더 구조

```
07_FitStep_Web/
├── app.py          ← 전체 화면 코드 (약 550줄)
├── api_client.py   ← 08 서버에 HTTP 요청 보내는 함수 모음
├── .env            ← 서버 주소(RAG_API_URL)와 비밀 키 저장
└── .streamlit/
    └── secrets.toml← Streamlit Cloud 배포용 환경변수
```

### 화면 구성

```
[로그인 페이지]
  → 아이디/비밀번호 입력
  → "새 프로필 만들기" 버튼 (회원가입)

[메인 메뉴] (로그인 후)
  → 대시보드 / 루틴 / 운동기록 / 헬스장설정 버튼

[루틴 페이지]
  → "오늘의 루틴 생성" 클릭
  → 운동 카드 표시 (이름, 부위, 세트, 횟수, 무게, 팁, GIF)
  → "운동 완료" 버튼 → 기록 저장

[대시보드]
  → 완료 루틴 수, 활동일, 연속 운동일 KPI 카드
  → Plotly 그래프 (무게 추이, 부위별 분포)

[헬스장 설정]
  → 기구명/수량/무게범위 입력
  → 저장하면 ChromaDB에 임베딩
```

### api_client.py — 08 서버 호출 함수 목록

```python
# 사용자
api_login(username, password)           → 로그인 (성공시 사용자 정보 반환)
api_save_user(...)                      → 회원가입
api_get_user(user_id)                   → 사용자 조회
api_update_weight(user_id, weight_kg)   → 체중 업데이트

# 루틴
api_save_routine(user_id, ...)          → 루틴 생성 & 저장
api_get_today_routine(user_id)          → 오늘 루틴 조회
api_complete_routine(routine_id)        → 루틴 완료 처리
api_delete_today_routine(user_id)       → 오늘 루틴 삭제

# 운동 기록
api_save_log(user_id, ...)              → 운동 기록 저장
api_get_recent_logs(user_id)            → 최근 기록 목록
api_get_stats(user_id)                  → 통계 (완료수, 활동일, 연속일)
api_get_progression(user_id)            → 진행 상황

# 기타
api_get_exercise_gif(name_kr, name_en)  → 운동 GIF URL
```

### 디자인 스타일

흰 배경 + 검정 글씨의 **블랙 & 화이트 미니멀** 스타일입니다.  
CSS를 직접 코드 안에 삽입해서 Streamlit 기본 디자인을 덮어씁니다.

```
배경: 흰색 (#ffffff)
버튼: 검정 (#000000) + 흰 글씨
입력창: 검정 테두리 (1.5px)
카드: 검정 테두리 + 둥근 모서리
```

---

## 6. 08_FitStep_API — 백엔드 서버 (FastAPI)

### 어떤 역할인가?

**모든 실제 처리**가 여기서 일어납니다.

- MySQL에 데이터 저장/조회
- ChromaDB에 헬스장 기구 벡터 저장/검색
- OpenAI API 호출
- 07_Web의 요청에 JSON으로 응답

### 폴더 구조

```
08_FitStep_API/
├── main.py          ← FastAPI 앱 시작점, 라우터 등록
├── db.py            ← MySQL 연결, 테이블 자동 생성
├── db_schemas.py    ← 데이터 형식 정의 (Pydantic 모델)
├── db_router.py     ← /db/* 엔드포인트 (사용자/루틴/기록/운동)
├── auth.py          ← API Key 인증 (X-API-Key 헤더)
├── indexing.py      ← 헬스장 기구 → ChromaDB 저장
├── retrieval.py     ← ChromaDB 검색 → 프롬프트용 텍스트 생성
├── schemas.py       ← 요청/응답 모델 (IndexRequest 등)
│
├── Dockerfile       ← 도커 이미지 빌드 설정
├── docker-compose.yml← MySQL + FastAPI 동시 실행 설정
├── .env             ← 비밀키, DB 접속정보 등
│
└── app/
    └── static/gifs/ ← 운동 GIF 파일들 (0006.gif ~ 1293.gif)
```

### API 엔드포인트 전체 목록

> **엔드포인트**란? 서버에 요청을 보내는 URL 주소입니다.  
> 예: `GET /db/users/1` → "1번 사용자 정보 주세요"

**헬스장 RAG (기구 정보)**
```
POST   /gym/index           → 헬스장 기구 정보를 ChromaDB에 저장
GET    /gym/retrieve/{id}   → ChromaDB에서 기구 정보 텍스트로 꺼내기
GET    /gym/exists/{id}     → 헬스장 데이터 있는지 확인
GET    /gym/data/{id}       → 저장된 헬스장 원본 데이터 조회
```

**사용자**
```
POST   /db/users            → 회원가입
POST   /db/users/login      → 로그인
GET    /db/users/{id}       → 사용자 정보 조회
GET    /db/users            → 전체 사용자 목록
PATCH  /db/users/{id}/weight→ 체중 업데이트
```

**루틴**
```
POST   /db/routines           → 루틴 저장
GET    /db/routines/today/{id}→ 오늘 루틴 조회
PATCH  /db/routines/{id}/complete → 루틴 완료 처리
DELETE /db/routines/today/{id}→ 오늘 루틴 삭제
```

**운동 기록**
```
POST   /db/logs                         → 운동 기록 저장
GET    /db/logs/routine/{id}/names      → 루틴에서 완료한 운동 이름 목록
GET    /db/logs/recent/{id}             → 최근 기록 조회
GET    /db/logs/recent-exercises/{id}   → 최근 7일 운동 목록
GET    /db/logs/stats/{id}              → 통계 (완료수/활동일/연속일)
GET    /db/logs/progression/{id}        → 운동별 진행 현황
GET    /db/logs/exercise-history/{id}/{name} → 특정 운동 이력
```

**운동 라이브러리**
```
POST   /db/exercises/sync   → 외부 API에서 운동 목록 가져와 DB에 저장
GET    /db/exercises/list   → 전체 운동 목록
GET    /db/exercises/gif    → 운동 GIF URL 조회
```

### 인증 방식

모든 요청에 **비밀 키**를 함께 보내야 합니다.

```
요청 헤더에 포함:
X-API-Key: 여기에_비밀번호_입력

키가 없거나 틀리면 → 401 Unauthorized (거절)
```

---

## 7. 데이터베이스 — 어디에 뭘 저장하나

### MySQL — 관계형 데이터 (표 형태)

엑셀 시트처럼 행/열로 저장하는 일반적인 DB입니다.

**테이블 4개:**

```
users (사용자)
  id / name / username / password_hash / age / gender
  height_cm / weight_kg / fitness_level / goal / health_notes / created_at

routines (루틴)
  id / user_id / routine_date / exercises_json / ai_advice
  is_completed / created_at

  * exercises_json: GPT가 만든 운동 목록을 JSON 텍스트로 저장
    예: [{"name":"스쿼트","sets":3,"reps":12,"weight_kg":80,"tip":"..."}]

workout_logs (운동 기록)
  id / user_id / routine_id / exercise_name
  sets_done / reps_done / weight_kg / note / logged_at

exercises (운동 라이브러리)
  id / name / name_en / category / body_part / gif_url / synced / created_at
```

**테이블 간 관계:**
```
users 1명 → routines 여러 개
routines 1개 → workout_logs 여러 개
exercises → workout_logs에서 exercise_name으로 참조
```

### ChromaDB — 벡터 데이터베이스 (의미 검색용)

일반 DB는 **정확히 일치**하는 것만 찾지만,  
ChromaDB는 **의미가 비슷한** 것을 찾습니다.

```
예: "덤벨로 할 수 있는 운동" 검색
→ "덤벨", "아령", "free weight" 관련 기구 모두 찾아냄
```

**저장 방식:**
```
헬스장 기구 텍스트
  "헬스장: 내 헬스장\n보유기구: 바벨, 덤벨, 스쿼트렉..."
        ↓ OpenAI text-embedding-3-small
  숫자 벡터로 변환 [0.12, -0.34, 0.89, ...]
        ↓
  ChromaDB에 저장 (user_id 메타데이터 포함)
```

---

## 8. AI가 루틴을 만드는 원리 (RAG)

### RAG가 뭔가요?

**RAG = Retrieval Augmented Generation**  
"찾아서 + 생성한다"는 뜻입니다.

GPT는 훈련 데이터만 알고, **내 헬스장에 어떤 기구가 있는지 모릅니다.**  
그래서 "내 헬스장 기구 정보"를 **직접 프롬프트에 넣어서** GPT가 참고하게 만듭니다.

### 전체 흐름

```
[1단계: 기구 저장]
사용자가 헬스장 기구 등록
  → ChromaDB에 임베딩 저장

[2단계: 루틴 생성 시]
ChromaDB에서 "이 사람 기구 정보" 텍스트로 꺼내기
  → MySQL에서 "이 사람 최근 운동 기록" 꺼내기
  → 아래 프롬프트 조립:

  ┌────────────────────────────────────────────────────┐
  │ 당신은 전문 헬스 트레이너입니다.                   │
  │                                                    │
  │ [사용자 정보]                                      │
  │ 나이: 28, 키: 165, 체중: 60, 수준: 초보            │
  │ 목표: 체지방 감소, 근육 증가                       │
  │                                                    │
  │ [헬스장 환경 — 이 기구만 사용하세요]               │
  │ 헬스장: 내 헬스장                                  │
  │ 보유기구: 바벨, 덤벨(2~40kg), 스쿼트렉...         │
  │                                                    │
  │ [최근 운동 기록]                                   │
  │ 스쿼트: 3세트 x 12회 x 80kg (어제)                │
  │ 벤치프레스: 3세트 x 10회 x 60kg (어제)            │
  │                                                    │
  │ 오늘의 4~6개 운동을 JSON으로 만들어 주세요.        │
  └────────────────────────────────────────────────────┘

  → GPT가 JSON 반환
  → MySQL에 저장 → 화면에 표시
```

---

## 9. Docker — 왜 쓰고 어떻게 돌아가나

### Docker가 뭔가요?

"내 컴퓨터에선 되는데 다른 컴퓨터에선 안 돼요" 문제를 해결하는 도구입니다.

앱 실행에 필요한 **모든 것(Python, 라이브러리, 설정)**을 하나의 **컨테이너(박스)** 안에 담아서,  
어떤 컴퓨터에서도 똑같이 실행되게 만듭니다.

### 비유

```
Docker 이미지 = 요리 레시피
Docker 컨테이너 = 레시피로 만든 요리

Dockerfile = 레시피를 작성한 문서
docker-compose.yml = 여러 요리를 동시에 내는 코스 메뉴
```

### 08_FitStep_API의 Docker 구성

`docker-compose.yml`이 두 개의 컨테이너를 동시에 실행합니다:

```
┌─────────────────────────────────────────┐
│          docker-compose.yml              │
│                                         │
│  ┌─────────────────┐  ┌──────────────┐  │
│  │  MySQL 컨테이너 │  │ FastAPI 컨테이너│  │
│  │  (fitstep_mysql)│  │ (gym_rag_api) │  │
│  │  포트: 3306     │  │ 포트: 3000   │  │
│  │  데이터: 영구저장│  │ 08 코드 실행 │  │
│  └─────────────────┘  └──────────────┘  │
│           ↑                  ↓           │
│        DB_HOST=mysql로 서로 연결됨       │
└─────────────────────────────────────────┘
```

**Dockerfile의 멀티스테이지 빌드:**
```
1단계 (builder): 라이브러리 설치 (용량 큰 빌드 도구 포함)
2단계 (runtime): 설치된 라이브러리만 복사 → 최종 이미지 크기 줄임
```

### 실행 명령어

```bash
# 08_FitStep_API 폴더에서

# 처음 시작 (이미지 빌드 + 컨테이너 실행)
docker compose up -d --build

# 이미 빌드된 것 그냥 시작
docker compose up -d

# 중지
docker compose down

# 로그 확인
docker compose logs -f
```

### 데이터 보존

Docker 컨테이너를 삭제해도 데이터가 사라지지 않도록 **볼륨(Volume)**을 사용합니다.

```yaml
volumes:
  mysql_data:    → MySQL 데이터 (운동 기록, 사용자 정보 등)
  chroma_data:   → ChromaDB 데이터 (헬스장 기구 임베딩)
```

---

## 10. Ngrok — 외부에서 접속하게 해주는 터널

### 왜 필요한가?

내 컴퓨터에서 `localhost:3000`으로 서버를 켜면, **내 컴퓨터 안에서만** 접속됩니다.  
Streamlit Cloud에 07을 배포하면, **클라우드 서버가 내 localhost에 접근할 수 없습니다.**

```
[Streamlit Cloud 서버] → localhost:3000 ← 접근 불가! (내 컴퓨터 밖)
```

**Ngrok**은 임시 공개 URL을 만들어서 이 문제를 해결합니다.

```
[Streamlit Cloud] → https://xxxx.ngrok.io → [내 컴퓨터 :3000]
                          ↑ Ngrok 터널
```

### 사용 방법

```bash
# 08 서버 먼저 실행 (Docker로)
docker compose up -d

# Ngrok으로 외부 공개
ngrok http 3000

# → 터미널에 표시됨:
# Forwarding  https://a1b2c3d4.ngrok.io → http://localhost:3000
```

그 URL(`https://a1b2c3d4.ngrok.io`)을 Streamlit Cloud의 **Secrets** 또는 `.env`의 `RAG_API_URL`에 입력하면 됩니다.

### 주의사항

- Ngrok 무료버전은 **컴퓨터를 끄면 URL이 바뀝니다**
- 컴퓨터가 꺼지면 서버도 꺼집니다 → Streamlit 앱도 작동 안 함
- 완전한 배포를 원하면 클라우드 서버(AWS, GCP 등)에 올려야 합니다

---

## 11. Streamlit — 화면을 만드는 방식

### Streamlit이 뭔가요?

Python 코드만으로 웹 화면을 만들 수 있는 라이브러리입니다.  
HTML/CSS/JavaScript를 몰라도 됩니다. (CSS 커스터마이징은 선택)

### 기본 원리

```python
import streamlit as st

# 제목 표시
st.title("FitStep")

# 버튼 만들기
if st.button("루틴 생성"):
    routine = api_save_routine(...)  # 08 서버에 요청
    st.write(routine)                # 결과 화면에 표시

# 입력창 만들기
username = st.text_input("아이디")
password = st.text_input("비밀번호", type="password")
```

### 화면 전환 방식

Streamlit은 페이지 전환 없이 **세션 상태(session_state)**로 현재 페이지를 관리합니다.

```python
# 로그인 성공 시
st.session_state["page"] = "main_menu"
st.session_state["user"] = {"id": 1, "name": "김효정"}

# 페이지 렌더링
if st.session_state["page"] == "main_menu":
    show_main_menu()
elif st.session_state["page"] == "routine":
    show_routine_page()
```

### 환경변수 관리

로컬 개발: `.env` 파일  
클라우드 배포: `.streamlit/secrets.toml` 파일

```toml
# .streamlit/secrets.toml
RAG_API_URL = "https://xxxx.ngrok.io"
RAG_API_KEY = "여기에_비밀번호_입력"
```

---

## 12. 전체 배포 흐름 한 눈에

### 로컬에서 전체 실행하기

```bash
# 1. 08 FastAPI 서버 시작
cd 08_FitStep_API
docker compose up -d --build
# → MySQL :3306, FastAPI :3000 켜짐

# 2. 07 Streamlit 웹앱 시작
cd 07_FitStep_Web
pip install -r requirements.txt
streamlit run app.py
# → 브라우저에서 localhost:8501 열림

# 3. 브라우저에서 확인
# http://localhost:8501
```

### Streamlit Cloud에 07 배포하기

```
1. 08을 로컬 Docker로 실행
2. Ngrok으로 공개 URL 생성
   ngrok http 3000

3. GitHub에 07_FitStep_Web 코드 push

4. https://streamlit.io/cloud 접속
   → New app → GitHub 저장소 → app.py 선택 → 배포

5. Secrets 탭에서 환경변수 설정:
   RAG_API_URL = "https://xxxx.ngrok.io"
   RAG_API_KEY = "여기에_비밀번호_입력"
```

### 포트 정리

| 서비스 | 포트 | 접속 주소 |
|-------|------|---------|
| MySQL | 3306 | localhost:3306 (직접 접속 불필요) |
| FastAPI (08) | 3000 | localhost:3000 |
| Streamlit (07) | 8501 | localhost:8501 |
| Ngrok 터널 | - | https://xxxx.ngrok.io → :3000 |

---

## 13. HTTP 메서드 — GET/POST/PATCH/DELETE 차이

API 요청에는 종류가 있습니다. 동사처럼 "어떤 행동을 할지" 알려줍니다.

| 메서드 | 의미 | 비유 | FitStep 예시 |
|--------|------|------|-------------|
| **GET** | 데이터 조회 | "정보 주세요" | `GET /db/users/1` → 1번 사용자 정보 가져오기 |
| **POST** | 데이터 생성 | "새로 만들어 주세요" | `POST /db/routines` → 오늘 루틴 생성 |
| **PATCH** | 일부 수정 | "이 부분만 바꿔 주세요" | `PATCH /db/users/1/weight` → 체중만 업데이트 |
| **DELETE** | 삭제 | "없애 주세요" | `DELETE /db/routines/today/1` → 오늘 루틴 삭제 |

> PUT도 있는데 이 프로젝트에선 안 씁니다. PUT은 "전체를 통째로 교체"하고, PATCH는 "일부만 수정"합니다.

### 요청과 응답의 구조

```
요청 (Request) — 07 → 08 로 보내는 것
┌────────────────────────────────────────┐
│ POST /db/logs                          │  ← 어디에 (URL + 메서드)
│ X-API-Key: 여기에_비밀번호_입력                 │  ← 헤더 (인증 키 등 부가 정보)
│                                        │
│ {                                      │
│   "user_id": 1,                        │  ← 바디 (실제 보내는 데이터)
│   "exercise_name": "스쿼트",           │
│   "sets_done": 3,                      │
│   "reps_done": 12,                     │
│   "weight_kg": 80.0                    │
│ }                                      │
└────────────────────────────────────────┘

응답 (Response) — 08 → 07 로 돌아오는 것
┌────────────────────────────────────────┐
│ 200 OK                                 │  ← 상태코드 (성공/실패)
│                                        │
│ { "ok": true }                         │  ← 바디 (결과 데이터)
└────────────────────────────────────────┘
```

### 상태코드 — 숫자로 결과를 알려줌

| 코드 | 의미 | 언제 발생하나 |
|------|------|-------------|
| **200** | 성공 | 요청 정상 처리 |
| **201** | 생성 성공 | POST로 새 데이터 만들었을 때 |
| **401** | 인증 실패 | X-API-Key 틀렸을 때 |
| **404** | 없음 | 존재하지 않는 사용자/루틴 조회 |
| **422** | 형식 오류 | JSON 형식이 잘못됐을 때 |
| **500** | 서버 에러 | 코드 버그, DB 연결 실패 등 |

---

## 14. 실제 데이터가 어떻게 생겼나 — JSON 예시

### 사용자 데이터 (users 테이블 한 행)

```json
{
  "id": 1,
  "name": "김효정",
  "username": "khyung",
  "age": 28,
  "gender": "female",
  "height_cm": 165.0,
  "weight_kg": 58.0,
  "fitness_level": "beginner",
  "goal": "체지방 감소, 근육 증가",
  "health_notes": "무릎 주의",
  "created_at": "2026-04-01T09:00:00"
}
```

### GPT가 만든 루틴 (routines.exercises_json 컬럼에 저장되는 텍스트)

```json
[
  {
    "name": "스쿼트",
    "name_en": "squats",
    "body_part": "하체",
    "sets": 3,
    "reps": 12,
    "weight_kg": 40.0,
    "tip": "무릎이 발끝을 넘지 않도록 주의하세요"
  },
  {
    "name": "덤벨 런지",
    "name_en": "dumbbell lunge",
    "body_part": "하체",
    "sets": 3,
    "reps": 10,
    "weight_kg": 8.0,
    "tip": "상체를 곧게 세우고 보폭을 넓게 유지하세요"
  },
  {
    "name": "덤벨 숄더 프레스",
    "name_en": "dumbbell shoulder press",
    "body_part": "어깨",
    "sets": 3,
    "reps": 12,
    "weight_kg": 6.0,
    "tip": "팔꿈치가 90도가 되도록 내리세요"
  }
]
```

> 이 JSON 전체가 하나의 텍스트 문자열로 DB에 저장됩니다.  
> 꺼낼 때 `json.loads()`로 다시 파이썬 리스트로 변환합니다.

### 헬스장 기구 등록 데이터 (ChromaDB에 들어가는 원본)

```json
{
  "gym_name": "내 헬스장",
  "equipment": [
    {
      "name": "바벨",
      "quantity": 2,
      "weight_range": "20~120kg",
      "notes": "올림픽 바벨"
    },
    {
      "name": "덤벨",
      "quantity": 20,
      "weight_range": "2~40kg",
      "notes": "2kg 단위"
    },
    {
      "name": "스쿼트렉",
      "quantity": 1,
      "weight_range": null,
      "notes": "안전바 있음"
    }
  ],
  "notes": "유산소 기구 없음"
}
```

### 운동 기록 (workout_logs 테이블 한 행)

```json
{
  "id": 42,
  "user_id": 1,
  "routine_id": 15,
  "exercise_name": "스쿼트",
  "sets_done": 3,
  "reps_done": 12,
  "weight_kg": 40.0,
  "note": "마지막 세트 힘들었음",
  "logged_at": "2026-04-22T19:30:00"
}
```

### 통계 응답 (GET /db/logs/stats/{user_id})

```json
{
  "completed_routines": 15,
  "total_logs": 87,
  "active_days": 12,
  "streak": 4
}
```

> `streak: 4` → 오늘 포함 4일 연속 운동했다는 뜻

---

## 15. 왜 이렇게 만들었나 — 설계 의도 Q&A

발표나 면접에서 "왜 이렇게 했어요?" 질문에 답할 수 있도록 정리했습니다.

---

**Q. 왜 프로젝트를 06/07/08로 세 개나 나눴나요?**

> 역할을 분리해서 **각자 독립적으로 발전**시킬 수 있기 때문입니다.  
> 화면(07)을 바꿔도 서버(08)에 영향이 없고,  
> 서버 내부를 바꿔도 화면 코드는 그대로 유지됩니다.  
> 이걸 "관심사 분리"라고 합니다.

---

**Q. MySQL이랑 ChromaDB를 왜 같이 쓰나요? 하나로 안 되나요?**

> 두 DB가 잘하는 게 다릅니다.
>
> - MySQL: "1번 사용자의 4월 기록 전부" 같은 **정확한 조건 검색**에 최적
> - ChromaDB: "이 헬스장 기구와 비슷한 운동 환경" 같은 **의미 기반 검색**에 최적
>
> GPT에게 "내 헬스장엔 이런 기구가 있어" 맥락을 정확히 전달하려면  
> 의미 검색이 가능한 ChromaDB가 필요합니다.

---

**Q. GPT한테 왜 JSON으로 응답하라고 하나요?**

> 앱이 GPT 응답을 **코드로 처리**해야 하기 때문입니다.  
> 자연어 문장으로 받으면 "스쿼트 3세트" 같은 정보를 파싱하기가 매우 어렵습니다.  
> JSON으로 받으면 `exercise["sets"]` 같이 바로 꺼내서 쓸 수 있습니다.

---

**Q. Docker를 왜 쓰나요? 그냥 pip install 하면 안 되나요?**

> MySQL과 FastAPI를 **동시에, 항상 같은 버전으로** 실행하기 위해서입니다.  
> pip install만 하면 Python 라이브러리만 설치되고,  
> MySQL은 별도로 설치·설정해야 해서 환경마다 달라질 수 있습니다.  
> Docker Compose로 묶으면 명령어 하나(`docker compose up`)로 전부 실행됩니다.

---

**Q. API Key 인증은 왜 필요한가요?**

> 08 서버가 인터넷에 노출되면(ngrok 등) 누구나 API를 호출할 수 있습니다.  
> API Key가 없으면 모르는 사람이 DB에 데이터를 마음대로 넣거나 지울 수 있습니다.  
> Key를 아는 사람(= 07 앱)만 요청을 허용하는 기본적인 보안 장치입니다.

---

**Q. exercises_json을 왜 별도 테이블로 안 만들고 JSON 문자열로 저장하나요?**

> 루틴마다 운동 개수와 속성이 달라서 **고정된 테이블 구조**로 만들기 어렵습니다.  
> GPT가 생성하는 운동 목록은 매번 다르기 때문에 유연한 JSON 텍스트로 저장하고,  
> 실제 기록(sets_done, reps_done 등)은 workout_logs 테이블에 정확하게 저장합니다.

---

**Q. 점진적 과부하를 왜 7.5% 올리나요?**

> 운동 과학에서 흔히 사용하는 **안전한 증가 비율**입니다.  
> 너무 많이 올리면 부상 위험이 있고, 너무 적게 올리면 효과가 없습니다.  
> 5~10% 사이가 일반적이며, 7.5%는 그 중간값입니다.

---

## 16. 에러가 났을 때 어디를 보나 — 트러블슈팅

### 문제별 확인 순서

**07 화면이 하얗게 뜨거나 에러 메시지가 나올 때**
```
1. 브라우저 주소창에 localhost:8501 확인
2. 터미널에서 streamlit run app.py 로그 확인
3. .env 파일에 RAG_API_URL이 제대로 설정됐는지 확인
4. 08 서버가 켜져 있는지 확인 → localhost:3000 접속해보기
```

**08 서버가 응답하지 않을 때**
```
1. docker compose ps  → 컨테이너 상태 확인
   (Up이면 실행 중, Exit면 종료된 것)

2. docker compose logs gym-rag-api  → 에러 로그 확인

3. docker compose logs mysql  → MySQL 에러 확인

4. 자주 나오는 에러:
   - "Can't connect to MySQL" → MySQL이 아직 준비 안 됨, 잠깐 기다리기
   - "Invalid API Key" → .env의 RAG_API_KEY 확인
   - "Address already in use" → 3000 포트를 다른 프로그램이 쓰고 있음
```

**루틴이 생성되지 않을 때**
```
1. OpenAI API Key가 유효한지 확인 (.env의 OPENAI_API_KEY)
2. OpenAI 크레딧이 남아 있는지 확인 (platform.openai.com)
3. 헬스장 기구를 등록했는지 확인 (헬스장 설정 페이지)
4. docker compose logs gym-rag-api 에서 "openai" 관련 에러 확인
```

**Ngrok 연결이 끊겼을 때**
```
1. ngrok을 다시 실행: ngrok http 3000
2. 새로 생긴 URL을 복사
3. Streamlit Cloud Secrets의 RAG_API_URL을 새 URL로 업데이트
4. Streamlit 앱 재시작 (Reboot app)
```

### 유용한 확인 명령어

```bash
# 실행 중인 컨테이너 목록
docker compose ps

# FastAPI 서버 로그 실시간 보기
docker compose logs -f gym-rag-api

# MySQL 로그 보기
docker compose logs mysql

# 컨테이너 전부 재시작
docker compose restart

# 완전히 지우고 다시 시작 (데이터는 보존됨)
docker compose down
docker compose up -d --build

# FastAPI 자동 문서 확인 (브라우저에서)
# http://localhost:3000/docs
```

### FastAPI 자동 문서 활용

FastAPI는 `/docs` 주소에서 **브라우저로 API를 직접 테스트**할 수 있습니다.

```
http://localhost:3000/docs

→ 모든 엔드포인트 목록이 보임
→ "Try it out" 버튼으로 직접 요청 전송 가능
→ 에러 확인, 응답 형식 확인에 유용
```

---

## 17. 자주 쓰는 용어 사전

| 용어 | 쉬운 설명 |
|------|---------|
| **API** | 서비스끼리 대화하는 약속된 방식. "이 주소로 이런 데이터 보내면 이런 응답 줄게" |
| **REST API** | URL로 요청하고 JSON으로 응답받는 가장 흔한 API 방식 |
| **FastAPI** | Python으로 REST API를 빠르게 만드는 프레임워크 |
| **Streamlit** | Python 코드로 웹 화면 만드는 라이브러리 |
| **MySQL** | 표(테이블) 형태로 데이터 저장하는 전통적인 DB |
| **ChromaDB** | 텍스트를 숫자 벡터로 바꿔서 "의미 검색"이 가능한 DB |
| **Docker** | 앱 실행 환경을 박스에 담아서 어디서든 똑같이 실행하게 함 |
| **컨테이너** | Docker로 실행 중인 하나의 앱 박스 |
| **이미지** | 컨테이너를 만들기 위한 설계도 |
| **Ngrok** | 내 컴퓨터 서버를 외부에서 접근 가능하게 터널 뚫어주는 도구 |
| **RAG** | AI가 모르는 내 데이터를 프롬프트에 직접 넣어서 참고하게 하는 기법 |
| **임베딩** | 텍스트를 숫자 벡터로 변환하는 것 (의미가 비슷하면 숫자도 비슷해짐) |
| **벡터** | 텍스트의 의미를 숫자 배열로 표현한 것 |
| **Pydantic** | Python에서 데이터 형식을 강제 검증하는 도구 ("나이는 숫자여야 해" 등) |
| **JSON** | 데이터를 주고받는 텍스트 형식. `{"이름": "김효정", "나이": 28}` |
| **엔드포인트** | API에서 요청을 받는 URL 주소 |
| **세션 상태** | Streamlit에서 페이지 이동 없이 데이터를 유지하는 방식 |
| **환경변수** | 코드에 직접 적으면 안 되는 비밀정보(API키, DB비밀번호)를 외부 파일에 보관하는 것 |
| **X-API-Key** | 08 서버에 요청할 때 헤더에 넣는 인증 키 |
| **CRUD** | Create(생성) / Read(조회) / Update(수정) / Delete(삭제) — DB 기본 4가지 조작 |
| **Docker Compose** | 여러 컨테이너를 한 번에 실행/관리하는 도구 |
| **볼륨(Volume)** | 컨테이너가 삭제돼도 데이터가 남도록 외부에 저장하는 공간 |
| **uvicorn** | FastAPI를 실행하는 서버 프로그램 (파이썬 웹서버) |
| **포트** | 컴퓨터 안의 "문 번호". 3000번 포트 = 3000번 문으로 들어오는 요청 처리 |
| **HTTP** | 웹에서 데이터를 주고받는 통신 규칙 |
| **헤더** | 요청/응답에 붙는 부가 정보. API Key, 콘텐츠 형식 등을 여기 담음 |
| **바디** | 요청/응답의 실제 데이터 내용 (보통 JSON 형식) |
| **상태코드** | 응답 결과를 숫자로 표현. 200=성공, 404=없음, 500=서버오류 |
| **프레임워크** | 개발을 편하게 해주는 틀. FastAPI, Streamlit 모두 프레임워크 |
| **라이브러리** | 남이 만들어 놓은 코드를 가져다 쓰는 것. `import`로 불러옴 |
| **requirements.txt** | 이 프로젝트에 필요한 라이브러리 목록. `pip install -r requirements.txt`로 한 번에 설치 |
| **localhost** | 내 컴퓨터 자신을 가리키는 주소. `127.0.0.1`과 같음 |
| **관심사 분리** | 역할별로 코드를 나눠서 서로 영향을 최소화하는 설계 원칙 |
| **프롬프트 엔지니어링** | GPT에게 보내는 지시문을 잘 설계해서 원하는 응답을 얻는 기술 |

---

> 이 가이드는 2026-04-22 기준 코드 분석을 토대로 작성되었습니다.  
> 06_FitStep / 07_FitStep_Web / 08_FitStep_API 세 프로젝트를 모두 포함합니다.
