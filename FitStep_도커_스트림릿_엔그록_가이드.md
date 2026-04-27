# Docker · Streamlit · ngrok 완전 이해 가이드
> 네트워크 기초 개념을 모르는 사람도 이해할 수 있게 작성했습니다.

---

## 읽기 전에: 네트워크 기초 개념 완전 정복.

> 이 파트를 이해하면 Docker, Streamlit, ngrok이 왜 그렇게 동작하는지 자연스럽게 이해됩니다.

---

### 기초 1: IP 주소란?

인터넷에 연결된 모든 기기(컴퓨터, 스마트폰, 서버)는 고유한 **IP 주소**를 가집니다.

```
내 컴퓨터:        192.168.0.5
친구 컴퓨터:      192.168.0.7
구글 서버:        142.250.196.110
```

> **비유:** IP 주소는 **집 주소**입니다. 택배를 보내려면 받는 사람의 주소가 있어야 하듯이, 인터넷에서 데이터를 보내려면 상대방의 IP 주소가 있어야 합니다.

**왜 숫자가 저렇게 생겼나요?**

IP 주소는 0~255 사이 숫자 4개를 점으로 구분한 형식입니다. (`xxx.xxx.xxx.xxx`)
사람이 외우기 어려워서 `google.com` 같은 도메인 이름으로 바꿔쓰지만, 실제로는 숫자 주소로 통신합니다.

---

### 기초 2: 포트(Port)란?

IP 주소가 "집 주소"라면, 포트는 **"집 안의 방 번호"**입니다.

하나의 컴퓨터에서 여러 프로그램이 동시에 인터넷과 통신할 수 있습니다. 포트가 없으면 어느 프로그램에게 데이터를 전달해야 할지 구분이 안 됩니다.

```
내 컴퓨터 (IP: 192.168.0.5) = 아파트 건물
  │
  ├── 포트 3000 → FastAPI 서버      (301호)
  ├── 포트 3306 → MySQL 데이터베이스 (302호)
  └── 포트 8501 → Streamlit 웹 화면 (303호)
```

**주소 전체 읽는 법:**

```
http://192.168.0.5:3000/db/users
       ───────────  ────  ────────
          IP 주소   포트   경로(어떤 기능?)
```

**자주 쓰는 포트 번호들:**

| 포트 | 용도 |
|------|------|
| 80 | 일반 웹사이트 (http) |
| 443 | 보안 웹사이트 (https) |
| 3306 | MySQL |
| 3000 | FitStep FastAPI 서버 |
| 8501 | Streamlit 웹 화면 |

> 포트 번호는 0~65535까지 있습니다. 1024 이하는 시스템 예약 번호라 보통 1025 이상을 씁니다.

**포트 충돌이란?**

같은 포트를 두 프로그램이 동시에 쓰려고 하면 오류가 납니다.

```
오류: "address already in use: 3000"
→ 3000번 포트를 이미 다른 프로그램이 쓰고 있다는 뜻
→ 해결: 기존 프로그램 종료 or 다른 포트 번호 사용
```

---

### 기초 3: localhost란?

`localhost` = **"지금 이 컴퓨터 자기 자신"**을 가리키는 특수 주소입니다.

숫자로는 `127.0.0.1`이고, `localhost`는 그 별명입니다.

```
http://localhost:3000
       ─────────  ────
       "내 컴퓨터"  포트 3000번
```

**핵심:** `localhost`는 **내 컴퓨터 안에서만** 통합니다. 외부 인터넷에서는 접근 불가입니다.

```
내 컴퓨터에서:    http://localhost:3000  → ✅ 접속 됨
친구 컴퓨터에서:  http://localhost:3000  → ❌ 접속 안 됨 (친구 컴퓨터의 3000번을 찾음)
인터넷에서:       http://localhost:3000  → ❌ 접속 안 됨
```

친구가 접속하게 하려면 `localhost` 대신 내 **실제 IP 주소**를 알려줘야 합니다.

```
친구에게: "http://192.168.0.5:3000 으로 접속해봐"
```

> 이게 바로 ngrok이 필요한 이유입니다. Streamlit Cloud(인터넷)에서 내 `localhost:3000`에 접근할 수 없으니까요.

---

### 기초 4: 클라이언트 vs 서버란?

웹 통신에서 항상 두 역할이 있습니다.

| 역할 | 설명 | FitStep에서는? |
|------|------|---------------|
| **클라이언트** | 요청을 보내는 쪽 | Streamlit 웹 화면 |
| **서버** | 요청을 받아서 처리하는 쪽 | FastAPI (08폴더) |

```
클라이언트 (Streamlit)          서버 (FastAPI)
       │                              │
       │  "1번 사용자 정보 줘!"        │
       │ ────────────────────────>    │
       │                              │  MySQL에서 조회
       │  {"name":"홍길동", ...}      │
       │ <────────────────────────    │
       │                              │
  화면에 표시                      요청 처리 완료
```

> **비유:** 클라이언트는 **손님**, 서버는 **직원**입니다. 손님이 주문하면(요청), 직원이 처리해서 가져다줍니다(응답).

---

### 기초 5: HTTP 요청이란?

클라이언트가 서버에게 보내는 "요청 편지"의 형식입니다.

**요청 편지 구조:**

```
[방법(Method)]  [주소(URL)]
GET  http://localhost:3000/db/users/1

→ "localhost:3000 서버에게, /db/users/1 경로로, 
   GET(조회) 요청을 보낸다"
→ 해석: "1번 사용자 정보 주세요"
```

**4가지 방법(Method):**

| Method | 의미 | 비유 | FitStep 예시 |
|--------|------|------|-------------|
| **GET** | 데이터 달라 | 도서관에서 책 빌리기 | `GET /db/users/1` → 1번 유저 조회 |
| **POST** | 새 데이터 만들어줘 | 도서관에 새 책 기증 | `POST /db/routines` → 루틴 저장 |
| **PATCH** | 일부만 수정해줘 | 책 일부 페이지만 교체 | `PATCH /db/users/1/weight` → 체중만 수정 |
| **DELETE** | 삭제해줘 | 책 폐기 요청 | `DELETE /db/routines/today/1` → 오늘 루틴 삭제 |

**응답(Response) 구조:**

```
서버가 돌려주는 답장:

상태코드: 200          ← 성공/실패 여부 (숫자로 표현)
내용:     {"id": 1, "name": "홍길동", "age": 25}
```

**자주 보는 상태코드:**

| 코드 | 의미 | 상황 |
|------|------|------|
| **200** | 성공 | 정상 처리됨 |
| **201** | 생성 성공 | 회원가입, 데이터 저장 완료 |
| **401** | 인증 실패 | API Key가 틀림 |
| **404** | 없음 | 존재하지 않는 사용자 ID 조회 |
| **500** | 서버 오류 | FastAPI 서버 내부 오류 |

---

### 기초 6: JSON이란?

클라이언트와 서버가 데이터를 주고받을 때 쓰는 **공통 언어(형식)**입니다.

```json
{
  "id": 1,
  "name": "홍길동",
  "age": 25,
  "goal": "근력 증가",
  "exercises": [
    {"name": "스쿼트", "sets": 3, "reps": 12},
    {"name": "벤치프레스", "sets": 3, "reps": 10}
  ]
}
```

- 중괄호 `{}` = 하나의 객체 (정보 묶음)
- 대괄호 `[]` = 목록
- `"키": 값` 형태로 정보를 표현

> **비유:** JSON은 **표준 양식지**입니다. 어느 나라 사람이든 같은 양식을 쓰면 서로 이해할 수 있듯이, 어떤 프로그래밍 언어든 JSON으로 데이터를 주고받으면 서로 이해합니다.

---

### 기초 7: API란?

**API(Application Programming Interface)** = 프로그램끼리 대화하는 창구

식당으로 비유하면:
- **메뉴판** = API 목록 (어떤 요청을 할 수 있는지)
- **주문** = API 요청
- **음식** = API 응답

FitStep의 API 목록 예시:

```
GET  /db/users/1          → "1번 유저 정보 주세요"
POST /db/routines         → "이 루틴 저장해주세요"
GET  /gym/retrieve/1      → "1번 유저 헬스장 기구 알려주세요"
GET  /health              → "서버 살아있어요?"
```

이 주소들을 **엔드포인트(Endpoint)**라고 부릅니다.

> **핵심 한 줄 요약:** IP=집 주소, 포트=방 번호, localhost=내 컴퓨터, HTTP=요청 방식, JSON=공통 데이터 형식, API=프로그램끼리 대화하는 창구.

---

## 1부: Docker 완전 이해

### Docker가 왜 필요한가?

**문제 상황 (Docker 없을 때):**

```
개발자 A 컴퓨터: Python 3.12, MySQL 8.0 → "잘 돼요!"
개발자 B 컴퓨터: Python 3.9,  MySQL 5.7 → "오류 나요!"
서버 컴퓨터:     Python 3.11, MySQL 8.0 → "다른 오류!"
```

같은 코드인데 환경이 달라서 다르게 동작하는 문제가 생깁니다.

**해결 (Docker 있을 때):**

```
Docker 컨테이너 = 코드 + Python 3.12 + MySQL 8.0 + 설정
                  → 어디서 실행해도 100% 동일한 환경
```

> **비유:** Docker는 **밀키트**입니다. 밀키트 박스 안에 재료(코드) + 레시피(설정) + 조리도구(라이브러리)가 전부 들어있어서, 누가 어느 주방에서 열어도 똑같은 요리가 나옵니다.

---

### 컨테이너(Container)란?

Docker가 만들어내는 "독립된 실행 환경"입니다.

```
내 컴퓨터
  ├── [컨테이너 1: fitstep_mysql]
  │     └── MySQL 8.0이 혼자 돌아가는 작은 가상 공간
  │
  └── [컨테이너 2: gym_rag_api]
        └── FastAPI 서버가 혼자 돌아가는 작은 가상 공간
```

- 컨테이너끼리는 서로 격리되어 있습니다
- 컨테이너를 삭제해도 내 컴퓨터 환경은 바뀌지 않습니다

> **비유:** 컨테이너는 **레고 블록 하나**입니다. 블록을 끼웠다 뺐다 해도 다른 블록에 영향을 주지 않습니다.

---

### 이미지(Image)란?

컨테이너를 만들기 위한 **설계도(틀)**입니다.

```
이미지 (설계도)  →  컨테이너 (실제로 돌아가는 것)
mysql:8.0       →  fitstep_mysql 컨테이너
Dockerfile      →  gym_rag_api 컨테이너
```

> **비유:** 이미지는 **붕어빵 틀**, 컨테이너는 **실제 붕어빵**입니다. 틀 하나로 붕어빵을 여러 개 찍어낼 수 있습니다.

---

### Dockerfile 읽는 법

[08_FitStep_API/Dockerfile](08_FitStep_API/Dockerfile)이 하는 일을 순서대로 설명하면:

```dockerfile
FROM python:3.12-slim          # ← "Python 3.12가 설치된 깨끗한 리눅스를 기반으로 시작해"

RUN apt-get install build-essential  # ← "필요한 도구 설치해"

COPY requirements.txt .        # ← "필요한 패키지 목록 파일 복사해"
RUN pip install -r requirements.txt  # ← "패키지 전부 설치해"

COPY app/ ./app/               # ← "내 FastAPI 코드 복사해"

EXPOSE 3000                    # ← "이 컨테이너는 3000번 포트를 사용할 거야"

CMD ["uvicorn", "app.main:app", "--port", "3000"]  # ← "컨테이너 실행하면 이 명령어로 서버 켜"
```

> **비유:** Dockerfile은 **이케아 조립 설명서**입니다. 1번부터 순서대로 따라하면 완성품(컨테이너)이 나옵니다.

---

### docker-compose.yml 읽는 법

여러 컨테이너를 한 번에 관리하는 설정 파일입니다.
[08_FitStep_API/docker-compose.yml](08_FitStep_API/docker-compose.yml)을 쉽게 풀면:

```yaml
services:

  mysql:                              # ← 컨테이너 이름: fitstep_mysql
    image: mysql:8.0                  # ← MySQL 8.0 이미지 사용 (직접 빌드 안 함)
    environment:
      MYSQL_ROOT_PASSWORD: ${...}     # ← 비밀번호 설정 (.env 파일에서 읽어옴)
      MYSQL_DATABASE: fitstep         # ← "fitstep" DB 자동 생성
    volumes:
      - mysql_data:/var/lib/mysql     # ← 데이터를 볼륨에 저장 (컨테이너 삭제해도 유지)

  gym-rag:                            # ← 컨테이너 이름: gym_rag_api
    build: .                          # ← 현재 폴더의 Dockerfile로 이미지 빌드
    ports:
      - "3000:3000"                   # ← 내 PC 3000번 = 컨테이너 3000번 연결
    environment:
      - DB_HOST=mysql                 # ← DB 주소를 "mysql"(위 서비스 이름)로 설정
    depends_on:
      mysql:
        condition: service_healthy    # ← MySQL이 완전히 켜진 후에 FastAPI 시작
```

**`"3000:3000"` 포트 매핑 이해하기:**

```
내 컴퓨터의 3000번 포트  →  컨테이너 안의 3000번 포트
(외부에서 접근하는 문)       (실제 서버가 열고 있는 문)
```

만약 `"8080:3000"`으로 바꾸면:
- `localhost:8080`으로 접근하면 → 컨테이너 3000번으로 연결됨

---

### 볼륨(Volume)이란?

컨테이너는 삭제하면 안에 있던 데이터도 사라집니다. 볼륨은 **데이터를 컨테이너 밖에 따로 보관**하는 방법입니다.

```
[컨테이너: fitstep_mysql]  ←→  [볼륨: mysql_data]
  컨테이너 삭제해도              데이터는 여기 남아있음
  데이터 유지됨
```

저장 위치: `/var/lib/docker/volumes/` (Docker가 관리하는 숨겨진 폴더)

> **비유:** USB 외장하드입니다. 노트북(컨테이너)이 망가져도 USB(볼륨)에 저장한 파일은 그대로입니다.

---

### Docker 자주 쓰는 명령어

```bash
# 컨테이너 실행 (코드 변경 후엔 --build 추가)
docker compose up -d
docker compose up -d --build

# 실행 중인 컨테이너 목록 확인
docker ps

# 컨테이너 로그 보기 (오류 확인할 때)
docker logs gym_rag_api
docker logs -f gym_rag_api    # -f: 실시간으로 계속 보기

# 컨테이너 중지
docker compose down

# 컨테이너 중지 + 볼륨(데이터)까지 삭제 (주의! 데이터 날아감)
docker compose down -v

# MySQL 직접 접속
docker exec -it fitstep_mysql mysql -u root -p fitstep
```

**`-d` 플래그란?** "백그라운드에서 실행"입니다. `-d` 없으면 터미널을 닫으면 컨테이너도 꺼집니다.

> **핵심 한 줄 요약:** Docker는 "환경 통일 + 한 번에 실행" 도구. `docker compose up -d --build`로 켜고, `docker compose down`으로 끈다.

---

## 2부: Streamlit 완전 이해

### Streamlit이란?

Python 코드로 웹 화면을 만들 수 있는 도구입니다. HTML/CSS/JavaScript를 몰라도 됩니다.

```python
# 이 코드 한 줄이 웹에서 버튼이 됩니다
if st.button("루틴 추천받기"):
    # 버튼 클릭 시 실행할 코드
    result = api_client.get_routine()
    st.write(result)
```

> **비유:** Streamlit은 **파워포인트**입니다. 복잡한 웹 개발 지식 없이도 슬라이드(화면)를 만들 수 있습니다.

---

### Streamlit이 화면을 그리는 방식

일반 웹과 달리 Streamlit은 **위에서 아래로 코드를 읽으면서 화면을 그립니다.**

```python
st.title("FitStep")          # ← 1. 제목 그리기
st.write("안녕하세요")        # ← 2. 텍스트 그리기

if st.button("클릭"):        # ← 3. 버튼 그리기
    st.success("클릭됨!")    # ← 4. 버튼 눌리면 이것도 그리기
```

버튼을 클릭하면 **전체 코드를 처음부터 다시 실행**합니다. 이게 Streamlit의 핵심 동작 방식입니다.

---

### session_state란?

코드가 매번 다시 실행되기 때문에, 변수도 매번 초기화됩니다. 로그인 상태를 유지하려면 `session_state`에 저장해야 합니다.

```python
# 이렇게 하면 안 됨 (코드 재실행 시 초기화됨)
user_id = None

# 이렇게 해야 함 (재실행해도 유지됨)
st.session_state.user_id = 1
```

FitStep에서 사용하는 session_state:

| 변수 | 저장하는 것 | 언제 저장? |
|------|-----------|----------|
| `st.session_state.user_id` | 로그인한 사용자 ID | 로그인 성공 시 |
| `st.session_state.user` | 사용자 정보 전체 | 로그인 성공 시 |
| `st.session_state.page` | 지금 어느 페이지인지 | 메뉴 클릭 시 |
| `st.session_state.today_result` | 오늘의 루틴 | 루틴 추천받을 때 |

> **비유:** session_state는 **포스트잇**입니다. 화면이 바뀌어도 포스트잇에 적어두면 잊어버리지 않습니다.

---

### secrets.toml이란?

API 키, 비밀번호 같은 민감한 정보를 저장하는 파일입니다.

**파일 위치:** `07_FitStep_Web/.streamlit/secrets.toml`

```toml
RAG_API_URL = "http://localhost:3000"
RAG_API_KEY = "내-비밀-키"
OPENAI_API_KEY = "sk-proj-..."
```

**코드에서 읽는 법:**
```python
url = st.secrets["RAG_API_URL"]
```

**중요:** 이 파일은 절대 GitHub에 올리면 안 됩니다. `.gitignore`에 등록되어 있습니다.

---

### 로컬 실행 vs 클라우드 배포의 차이

| | 로컬 실행 | Streamlit Cloud |
|---|---|---|
| 접속 주소 | `http://localhost:8501` | `https://앱이름.streamlit.app` |
| 환경변수 읽는 곳 | `.env` 파일 또는 `secrets.toml` | 클라우드 설정창에서 입력한 Secrets |
| FastAPI 서버 주소 | `http://localhost:3000` | ngrok 터널 주소 |
| 다른 사람 접속 가능? | 불가 (내 컴퓨터 안에서만) | 가능 (전 세계 어디서나) |

**app.py 상단 코드가 두 환경을 자동으로 처리하는 방법:**

```python
# 1. 로컬이면 .env에서 읽기
load_dotenv()

# 2. Streamlit Cloud면 secrets에서 읽기
if "RAG_API_URL" in st.secrets:
    os.environ["RAG_API_URL"] = st.secrets["RAG_API_URL"]
```

→ 어떤 환경이든 `os.environ["RAG_API_URL"]`로 통일됩니다.

> **핵심 한 줄 요약:** Streamlit은 Python으로 웹 화면 만드는 도구. 로컬은 localhost:8501, 클라우드 배포하면 누구나 접속 가능.

---

## 3부: ngrok 완전 이해

### 왜 ngrok이 필요한가?

**문제:** Streamlit Cloud는 인터넷에 있고, FastAPI 서버는 내 컴퓨터에 있습니다.

```
Streamlit Cloud (인터넷 어딘가)
        ↓
  "FastAPI 서버 주세요"
        ↓
  localhost:3000 ???  ← 인터넷에서 localhost는 찾을 수 없음!
```

`localhost`는 내 컴퓨터 안에서만 통하는 주소라서, 외부 인터넷에서는 접근이 불가합니다.

**해결책: ngrok**

ngrok은 내 컴퓨터의 포트를 인터넷에서 접근 가능한 주소로 연결해주는 **터널**입니다.

```
Streamlit Cloud
        ↓
https://abc123.ngrok.io   ← 인터넷에서 접근 가능한 주소
        ↓ (ngrok 터널)
내 컴퓨터 localhost:3000   ← FastAPI 서버
```

> **비유:** ngrok은 **지하통로**입니다. 외부(인터넷)에서 직접 들어올 수 없는 내 방(localhost)에, 외부와 연결된 비밀 통로를 뚫어주는 것입니다.

---

### ngrok 동작 원리 (그림으로)

```
[사용자 브라우저]
      │ 클릭
      ▼
[Streamlit Cloud]  ──────────────────────────────────────────────────────┐
      │                                                                   │
      │ HTTP 요청 → https://abc123.ngrok.io/db/users/login               │
      ▼                                                                   │
[ngrok 서버 (인터넷)]                                                     │
      │                                                                   │
      │ 터널을 통해 전달                                                    │
      ▼                                                                   │
[내 컴퓨터 ngrok 프로세스]  ←── 인터넷 ↔ 내 PC 사이의 연결 유지 중         │
      │                                                                   │
      │ localhost:3000으로 전달                                            │
      ▼                                                                   │
[Docker: gym_rag_api]  ← FastAPI 서버가 처리하고 응답 반환 ───────────────┘
```

---

### ngrok 사용법

```bash
# 1. ngrok 실행 (3000번 포트를 인터넷에 노출)
ngrok http 3000
```

실행하면 터미널에 이렇게 나타납니다:

```
Session Status    online
Forwarding        https://abc123-456.ngrok-free.app -> http://localhost:3000
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                  이 주소를 복사해서 Streamlit Cloud Secrets에 붙여넣기!
```

```bash
# 2. Streamlit Cloud Secrets 업데이트
RAG_API_URL = "https://abc123-456.ngrok-free.app"
```

---

### ngrok의 치명적 단점

**ngrok을 재시작하면 주소가 바뀝니다.**

```
# 오늘
https://abc123.ngrok-free.app

# ngrok 재시작 후
https://xyz789.ngrok-free.app  ← 완전히 다른 주소!
```

그래서 ngrok을 껐다 켤 때마다 **Streamlit Cloud Secrets의 `RAG_API_URL`을 새 주소로 업데이트**해야 합니다.

**고정 주소를 쓰려면:** ngrok 유료 플랜(Static Domain)을 사용하면 주소가 고정됩니다.

---

### ngrok 없이 배포하는 방법

장기적으로 운영할 계획이라면 ngrok 대신 아래 방법을 사용합니다:

| 방법 | 설명 | 비용 |
|------|------|------|
| AWS EC2 / GCP VM | 클라우드 서버에 직접 Docker 실행 | 월 몇 달러 ~ |
| Railway / Render | GitHub에 push하면 자동 배포 | 무료 플랜 있음 |
| ngrok 유료 플랜 | 고정 주소 제공 | 월 $8~ |

> **핵심 한 줄 요약:** ngrok은 내 컴퓨터를 임시 서버로 만들어주는 터널. 재시작하면 주소가 바뀌니 Secrets 업데이트 필요.

---

## 4부: 세 가지를 합쳐서 이해하기

### 전체 그림 (로컬 개발 시)

```
내 컴퓨터
│
├── [터미널 1] streamlit run app.py
│     → 브라우저: http://localhost:8501
│
├── [터미널 2] docker compose up -d
│     → MySQL 컨테이너 (포트 3306)
│     → FastAPI 컨테이너 (포트 3000)
│
└── [브라우저] localhost:8501 접속
      → Streamlit 화면 렌더링
      → 버튼 클릭 시 localhost:3000으로 API 호출
      → FastAPI가 MySQL/ChromaDB 처리 후 응답
```

---

### 전체 그림 (Streamlit Cloud 배포 시)

```
내 컴퓨터
│
├── [터미널 1] docker compose up -d
│     → MySQL + FastAPI 컨테이너 실행
│
├── [터미널 2] ngrok http 3000
│     → https://abc123.ngrok.io 터널 생성
│
└── 이 두 터미널은 계속 켜 둬야 합니다!

인터넷
│
├── Streamlit Cloud (https://내앱.streamlit.app)
│     → GitHub 코드 자동 배포
│     → secrets.toml의 RAG_API_URL로 API 호출
│
└── ngrok 터널 → 내 컴퓨터 localhost:3000 → FastAPI
```

---

### 어떤 파일에 어떤 주소를 쓰는지 정리

| 상황 | `secrets.toml`의 `RAG_API_URL` | FastAPI 접근 가능 여부 |
|------|-------------------------------|----------------------|
| 로컬 개발 | `http://localhost:3000` | 내 컴퓨터에서만 |
| Cloud 배포 | `https://abc123.ngrok.io` | 전 세계 어디서나 |

---

## 5부: 자주 겪는 문제와 해결법

### "연결이 안 돼요" 오류

```
ConnectionError: http://localhost:3000 에 연결 실패
```

**체크리스트:**
1. Docker가 켜져 있나요? → `docker ps` 로 확인
2. 컨테이너가 실행 중인가요? → `gym_rag_api`, `fitstep_mysql` 둘 다 `Up` 상태여야 함
3. 포트가 맞나요? → `secrets.toml`의 `RAG_API_URL` 확인

---

### "ngrok URL이 작동 안 해요" 오류

**원인 1:** ngrok을 재시작해서 주소가 바뀜
→ 새 ngrok 주소를 Streamlit Cloud Secrets에 업데이트

**원인 2:** Docker 컨테이너가 꺼져 있음
→ `docker compose up -d` 로 다시 실행

**원인 3:** ngrok 프로세스가 꺼져 있음
→ `ngrok http 3000` 다시 실행

---

### "데이터가 사라졌어요"

**컨테이너를 `docker compose down -v`로 삭제한 경우:** 볼륨까지 삭제되어 데이터 복구 불가

**컨테이너를 `docker compose down`으로 삭제한 경우:** 볼륨은 남아있으므로 `docker compose up -d` 로 다시 실행하면 데이터 복구됨

→ 습관적으로 `-v` 옵션 없이 `docker compose down`만 사용하세요.

---

### Docker 컨테이너 안을 들여다보고 싶을 때

```bash
# MySQL 접속해서 데이터 확인
docker exec -it fitstep_mysql mysql -u root -p fitstep

# FastAPI 컨테이너 내부 터미널 접속
docker exec -it gym_rag_api /bin/sh

# 실시간 로그 보기
docker logs -f gym_rag_api
```

---

## 한 눈에 보는 정리표

| 기술 | 한 줄 설명 | 없으면? |
|------|-----------|--------|
| **Docker** | MySQL + FastAPI를 한 번에 실행하는 컨테이너 도구 | 각자 설치하고 버전 맞춰야 함 |
| **docker-compose.yml** | 어떤 컨테이너를 어떻게 실행할지 설정 파일 | 컨테이너 하나씩 수동 실행 |
| **Dockerfile** | FastAPI 이미지를 만드는 설명서 | 이미지 빌드 불가 |
| **볼륨(Volume)** | 컨테이너 데이터를 영구 보존하는 저장소 | 컨테이너 재시작 시 데이터 삭제 |
| **Streamlit** | Python으로 웹 화면 만드는 도구 | HTML/CSS/JS 직접 짜야 함 |
| **session_state** | 페이지 이동해도 로그인 유지되게 하는 임시 메모 | 클릭할 때마다 로그아웃됨 |
| **secrets.toml** | API 키 등 비밀 정보 저장 파일 | 코드에 키 직접 노출됨 |
| **ngrok** | 내 컴퓨터를 인터넷에 임시 노출하는 터널 | Streamlit Cloud에서 FastAPI 못 씀 |
| **포트** | 어느 프로그램에 연결할지 구분하는 번호 | 주소가 겹쳐서 충돌 발생 |
| **localhost** | 지금 내 컴퓨터를 가리키는 특수 주소 | - |

---

## 전체 실행 순서 (복붙용 치트시트)

### 로컬 개발 시

```bash
# 1. FastAPI + MySQL 실행
cd /Users/hyojeong/ax-workspace/08_FitStep_API
docker compose up -d --build

# 2. 실행 확인
docker ps
curl http://localhost:3000/health

# 3. Streamlit 실행 (다른 터미널)
cd /Users/hyojeong/ax-workspace/07_FitStep_Web
streamlit run app.py

# 4. 브라우저 접속: http://localhost:8501
```

### Streamlit Cloud 배포 시

```bash
# 1. FastAPI + MySQL 실행
cd /Users/hyojeong/ax-workspace/08_FitStep_API
docker compose up -d --build

# 2. ngrok 터널 실행 (다른 터미널, 계속 켜둬야 함)
ngrok http 3000
# → 표시된 https://xxxx.ngrok-free.app 주소 복사

# 3. Streamlit Cloud Secrets 업데이트
# https://share.streamlit.io → 앱 설정 → Secrets
# RAG_API_URL = "https://xxxx.ngrok-free.app"

# 4. Streamlit Cloud에서 Reboot app 클릭
```

### 종료 시

```bash
# Streamlit 로컬: Ctrl+C
# ngrok: Ctrl+C
# Docker:
docker compose down
```
