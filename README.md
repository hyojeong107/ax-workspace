# ax-workspace

AI/LLM을 활용한 미니 프로젝트 모음입니다. 게임, 챗봇, 알림 서비스 등 다양한 실습 프로젝트를 포함합니다.

---

## 프로젝트 목록

### 01. Tetris (`01_tetris/`)
Python + Pygame으로 구현한 테트리스 게임입니다.
- 키보드 입력 처리, 게임 루프, 점수 및 최고 점수 저장 기능 포함
- 실행: `python 01_tetris/main.py`

---

### 03. AX 교육 커리큘럼 챗봇 (`03_ax_curriculum_chatbot/`)
기업의 AI Transformation(AX) 교육 커리큘럼을 설계해주는 CLI 챗봇입니다.
- OpenAI GPT-4o 기반
- 기업 유형, 교육 대상, 목표, 시간 등을 단계적으로 수집해 맞춤 커리큘럼 제안
- 실행: `python 03_ax_curriculum_chatbot/main.py`

---

### 04. 영화 상영 알림 봇 (`04_movie_timer/`)
관심 영화를 등록하고, 상영 종료 임박 시 터미널 알림을 받는 CLI 챗봇입니다.
- OpenAI GPT-4o Function Calling + KOBIS 오픈API 활용
- D-7/D-3/D-1 기준 알림, 매일 오전 9시 자동 체크, 예매 링크 제공
- 실행: `cd 04_movie_timer/movie_alert_bot && python main.py`

---

### 05. 독서 가이드 멘토 챗봇 (`05_book_guide_mentor/`)
사용자 맞춤형 도서를 추천하고 독서 로드맵을 제공하는 CLI 챗봇입니다.
- OpenAI GPT-4o + 카카오 도서 검색 API 활용
- 관심 주제, 수준, 선호 형식, 독서 목적을 설문 후 실제 도서 정보와 함께 추천
- 실행: `python 05_book_guide_mentor/main.py`

---

## 공통 환경 설정

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 환경 변수 (`.env` 파일)
프로젝트별 폴더에 `.env` 파일을 생성하여 아래 키를 설정하세요.

| 키 | 설명 | 사용 프로젝트 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 | 03, 04, 05 |
| `KOBIS_API_KEY` | KOBIS 영화 오픈API 키 | 04 |
| `KAKAO_API_KEY` | 카카오 REST API 키 | 05 |
