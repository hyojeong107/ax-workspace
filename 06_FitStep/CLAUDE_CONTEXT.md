# FitStep — Claude 새 세션 컨텍스트

아래 내용을 새 Claude 세션 시작 시 붙여넣으세요.

---

## 프로젝트 요약

**FitStep** — Streamlit + MySQL + OpenAI 기반 AI 헬스 코치 웹앱.

- 실행: `start.bat` → FastAPI(port 8000) + Streamlit(`06_FitStep/streamlit_app/app.py`) 동시 실행
- Python venv: `ax-workspace/venv/`
- 작업 디렉토리: `C:\Users\user\Desktop\dev\ax-workspace\ax-workspace\06_FitStep`

---

## 파일 구조 (핵심만)

```
06_FitStep/
├── streamlit_app/
│   ├── app.py               # 메인 진입점, 사이드바, 페이지 라우터
│   ├── components.py        # 전역 CSS + 재사용 UI 컴포넌트 함수
│   └── pages/
│       ├── dashboard.py     # KPI 카드 + Plotly 차트 (운동 통계)
│       ├── routine.py       # AI 루틴 추천 (GPT 호출)
│       ├── workout_log.py   # 운동 기록 입력 + 히스토리
│       ├── gym_setup.py     # 헬스장 기구 등록 (JSON + ChromaDB)
│       └── user_setup.py   # 사용자 프로필 생성/선택
├── db/
│   ├── database.py          # MySQL 연결, init_db() (테이블 생성)
│   └── user_repo.py         # save_user, get_user, get_all_users 등
├── modules/
│   ├── recommender.py       # recommend_routine() — GPT 호출 핵심
│   ├── progression.py       # get_overall_progress_summary, analyze_progression
│   └── gym_setup.py         # get_gym_profile()
└── rag/
    └── gym_rag.py           # ChromaDB 기반 헬스장 기구 벡터 검색
```

---

## 현재 디자인 테마 (Light Neo-Brutalist)

| 토큰 | 값 | 용도 |
|------|----|------|
| BG | `#F5F0EB` | 전체 배경 (크림) |
| SURFACE | `#FFFFFF` | 카드 배경 |
| ACCENT | `#FF4500` | 버튼, 강조색 (레드-오렌지) |
| DARK | `#1A1A1A` | 텍스트, 테두리 |
| MUTED | `#888888` | 보조 텍스트 |
| BORDER | `#E8E0D8` | 구분선 |

**카드 스타일**: `border: 2px solid #1A1A1A`, `box-shadow: 4px 4px 0 #1A1A1A` (neo-brutalist offset shadow)

**폰트**: Space Grotesk (제목/숫자 굵게) + DM Sans (본문)

---

## DB 스키마 (MySQL, db명: `fitstep`)

```sql
users        (id, name, username, password_hash, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes, created_at)
exercises    (id, name, name_en, category, difficulty, equipment, description)
routines     (id, user_id, routine_date, exercises_json, ai_advice, is_completed, created_at)
workout_logs (id, user_id, routine_id, exercise_name, sets_done, reps_done, weight_kg, note, logged_at)
```

---

## 주요 패턴 / 주의사항

1. **CSS 주입**: `st.html(GLOBAL_CSS)` 사용 (Streamlit 1.35+에서 `st.markdown`의 `<style>` 차단됨)
2. **사이드바 버튼 CSS**: `[data-testid="stSidebar"] .stButton > button` — 반드시 사이드바 전용 셀렉터 사용, 안 하면 메인 버튼도 같이 덮어씌워짐
3. **Plotly 레이아웃**: `update_layout(**PLOTLY_LAYOUT, xaxis=dict(...))` 하면 키 중복 TypeError → 반드시 dict 머지 후 전달:
   ```python
   layout = {**PLOTLY_LAYOUT, "height": 220}
   layout["xaxis"] = {**PLOTLY_LAYOUT["xaxis"], "tickformat": "%m/%d"}
   fig.update_layout(**layout)
   ```
4. **f-string 안에 dict 리터럴 금지**: `f"{{"key":"val"}.get(...)}"` → SyntaxError. 반드시 변수로 추출 후 사용
5. **get_all_users()**: `SELECT id, name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes` — age/BMI 표시에 필요한 컬럼 모두 포함

---

## 테마 교체 시 수정 파일 목록

색상 변경 시 아래 파일의 하드코딩 색상값을 교체해야 함:

- `streamlit_app/components.py` — GLOBAL_CSS + 모든 컴포넌트 함수
- `streamlit_app/app.py` — 사이드바 마크업
- `streamlit_app/pages/dashboard.py` — PLOTLY_LAYOUT + 차트 색상
- `streamlit_app/pages/routine.py` — 인라인 스타일
- `streamlit_app/pages/workout_log.py` — 인라인 스타일
- `streamlit_app/pages/gym_setup.py` — 인라인 스타일
- `streamlit_app/pages/user_setup.py` — 프로필 카드 스타일

> 💡 테마 교체 토큰 절약 팁: "theme.py 중앙화 리팩토링을 먼저 해줘" 라고 요청하면
> 이후 테마 교체 시 파일 1개만 수정하면 됩니다.

---

## 세션 시작 시 요청 예시

```
위 CLAUDE_CONTEXT.md를 읽었어. FitStep 프로젝트야.
오늘 작업: [여기에 작업 내용 적기]
```
