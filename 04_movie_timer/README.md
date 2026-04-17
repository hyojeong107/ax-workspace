# 영화 상영 알림 서비스

관심 영화를 등록하면 상영 종료 임박 시 터미널 알림을 받을 수 있는 CLI 챗봇입니다.
OpenAI gpt-4o Function Calling과 KOBIS 오픈API를 활용합니다.

---

## 설치 및 실행

### 1. 의존성 설치

```
pip install -r movie_alert_bot/requirements.txt
```

### 2. 환경 변수 설정

`movie_alert_bot/` 폴더 안에 `.env` 파일을 생성합니다.

```
OPENAI_API_KEY=sk-...
KOBIS_API_KEY=...
```

- **OPENAI_API_KEY**: 필수. [OpenAI 플랫폼](https://platform.openai.com/)에서 발급
- **KOBIS_API_KEY**: 선택. 없으면 영화 검색 기능이 제한됩니다. [KOBIS 오픈API](https://www.kobis.or.kr/kobisopenapi/homepg/apiservice/searchServiceInfo.do)에서 발급

### 3. 실행

```
cd movie_alert_bot
python main.py
```

---

## 사용법

프로그램을 실행하면 챗봇과 자연어로 대화할 수 있습니다.

### 영화 등록

```
사용자: 베테랑2 등록해줘
```

챗봇이 KOBIS에서 영화를 검색해 결과를 보여준 뒤 확인 후 등록합니다.

### 관심 목록 조회

```
사용자: 등록된 영화 보여줘
```

### 영화 삭제

```
사용자: 베테랑2 삭제해줘
```

### 선호 극장 설정

```
사용자: CGV랑 메가박스로 설정해줘
```

지원 극장: **CGV**, **롯데시네마**, **메가박스**

### 선호 극장 조회

```
사용자: 지금 극장 설정 어떻게 돼있어?
```

### 상영 종료 임박 알림 즉시 확인

```
사용자: 지금 알림 있어?
```

D-7, D-3, D-1 기준으로 종료 임박 영화를 알려줍니다.

### 예매 URL 조회

```
사용자: 베테랑2 예매 링크 알려줘
```

### 상영 종료일 수정

```
사용자: 베테랑2 종료일 2025-05-31로 바꿔줘
```

---

## 자동 알림

프로그램이 실행 중인 동안 **매일 오전 9시**에 자동으로 관심 영화의 상영 종료일을 체크합니다.
D-7, D-3, D-1에 해당하는 영화가 있으면 터미널에 알림과 예매 링크를 출력합니다.

---

## 종료

```
Ctrl+C  또는  "종료" 입력
```

---

## 데이터 저장 위치

| 파일 | 내용 |
|---|---|
| `movie_alert_bot/data/watchlist.json` | 관심 영화 목록 |
| `movie_alert_bot/data/config.json` | 선호 극장 설정 |
