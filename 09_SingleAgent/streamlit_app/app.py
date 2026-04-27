"""
FitStep Single Agent · Streamlit UI
단일 AI 에이전트와의 대화로 맞춤형 운동 커리큘럼 생성
"""

import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv

# ── 환경 설정 ─────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"), override=True)

# Streamlit Cloud secrets 지원
try:
    for _k in ["AGENT_API_URL", "JWT_SECRET_KEY"]:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

sys.path.insert(0, _HERE)
import api_client

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitStep · Single Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.agent-bubble { background: #f0f4ff; border-radius: 12px; padding: 12px 16px; margin: 8px 0; }
.user-bubble  { background: #e8f5e9; border-radius: 12px; padding: 12px 16px; margin: 8px 0; text-align: right; }
.tool-tag     { display: inline-block; background: #6c63ff22; color: #6c63ff; border-radius: 6px;
                padding: 2px 8px; font-size: 0.78rem; margin: 2px; }
.curriculum-card { background: #fff8e1; border-left: 4px solid #ffc107; border-radius: 8px;
                   padding: 12px 16px; margin: 8px 0; }
.valid-badge   { color: #2e7d32; font-weight: bold; }
.invalid-badge { color: #c62828; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Session State 초기화 ──────────────────────────────────────────────────────
for key, default in [
    ("logged_in", False),
    ("token", None),
    ("messages", []),
    ("user_profile", None),
    ("gym_data", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── 사이드바: 로그인 & 프로필 ─────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 FitStep Agent")

    # API 상태
    api_ok = api_client.health_check()
    st.caption(f"API: {'🟢 정상' if api_ok else '🔴 연결 불가'}")
    st.divider()

    if not st.session_state.logged_in:
        st.subheader("로그인")
        username = st.text_input("아이디", value="demo")
        password = st.text_input("비밀번호", type="password", value="demo1234")
        if st.button("로그인", use_container_width=True):
            token = api_client.login(username, password)
            if token:
                st.session_state.logged_in = True
                st.session_state.token = token
                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("로그인 실패. 아이디/비밀번호를 확인하세요.")
    else:
        st.success(f"✅ 로그인됨")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.token = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("내 프로필")
        with st.form("profile_form"):
            age = st.number_input("나이", 10, 100, 30)
            gender = st.selectbox("성별", ["M", "F"], format_func=lambda x: "남성" if x == "M" else "여성")
            height = st.number_input("키 (cm)", 100.0, 250.0, 170.0, step=0.1)
            weight = st.number_input("몸무게 (kg)", 30.0, 200.0, 65.0, step=0.1)
            bmi = round(weight / (height / 100) ** 2, 1)

            def _bmi_grade(b):
                if b < 18.5: return "저체중"
                if b < 23: return "정상"
                if b < 25: return "과체중"
                if b < 30: return "비만"
                return "고도비만"

            def _age_group(a):
                decade = (a // 10) * 10
                return f"{decade}대"

            st.caption(f"BMI: {bmi} ({_bmi_grade(bmi)})")
            special = st.text_area("특이사항 (부상, 질환 등)", height=60)

            if st.form_submit_button("프로필 저장"):
                st.session_state.user_profile = {
                    "age": age,
                    "gender": gender,
                    "height": height,
                    "weight": weight,
                    "bmi": bmi,
                    "age_group": _age_group(age),
                    "bmi_grade": _bmi_grade(bmi),
                    "special_notes": special,
                }
                st.success("프로필 저장됨!")

        st.divider()
        st.subheader("헬스장 기구")
        gym_input = st.text_area(
            "보유 기구 목록 (쉼표 구분)",
            placeholder="예: 바벨, 덤벨, 트레드밀, 풀업바",
            height=80,
        )
        if st.button("기구 정보 저장"):
            if gym_input.strip():
                equipment = [e.strip() for e in gym_input.split(",") if e.strip()]
                st.session_state.gym_data = {"equipment": equipment}
                st.success(f"{len(equipment)}개 기구 저장됨!")


# ── 메인: 대화 화면 ───────────────────────────────────────────────────────────
st.title("🤖 FitStep Single Agent")
st.caption("AI 에이전트와 대화하며 맞춤형 운동 커리큘럼을 생성하세요.")

if not st.session_state.logged_in:
    st.info("👈 왼쪽 사이드바에서 로그인 후 이용하세요. (데모: demo / demo1234)")
    st.stop()

# 대화 이력 표시
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    extra = msg.get("extra", {})

    if role == "user":
        st.markdown(f'<div class="user-bubble">👤 {content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="agent-bubble">🤖 {content}</div>', unsafe_allow_html=True)

        # 호출된 도구 태그
        tool_calls = extra.get("tool_calls_made", [])
        if tool_calls:
            tags = "".join(f'<span class="tool-tag">🔧 {t}</span>' for t in tool_calls)
            st.markdown(f"<div>{tags}</div>", unsafe_allow_html=True)

        # 커리큘럼 표시
        curriculum = extra.get("curriculum")
        if curriculum and "error" not in curriculum:
            with st.expander("📋 생성된 커리큘럼 보기", expanded=True):
                st.markdown(f'<div class="curriculum-card">', unsafe_allow_html=True)
                summary = curriculum.get("summary", "")
                if summary:
                    st.markdown(f"**요약:** {summary}")
                weekly_plan = curriculum.get("weekly_plan", [])
                for session in weekly_plan:
                    st.markdown(f"**{session.get('day', '')} — {session.get('focus', '')}** ({session.get('duration_minutes', 0)}분)")
                    for ex in session.get("exercises", []):
                        reps = ex.get('reps', '')
                        rest = ex.get('rest_seconds', 0)
                        note = ex.get('notes', '')
                        line = f"  - {ex.get('name', '')} {ex.get('sets', 0)}세트 × {reps}회, 휴식 {rest}초"
                        if note:
                            line += f" *(주의: {note})*"
                        st.markdown(line)
                notes = curriculum.get("notes", "")
                if notes:
                    st.info(f"📌 {notes}")
                st.markdown("</div>", unsafe_allow_html=True)

                # JSON 다운로드
                st.download_button(
                    "⬇ JSON 다운로드",
                    data=json.dumps(curriculum, ensure_ascii=False, indent=2),
                    file_name="curriculum.json",
                    mime="application/json",
                )

        # 검증 결과
        vr = extra.get("validation_result")
        if vr:
            if vr.get("is_valid"):
                st.markdown('<span class="valid-badge">✅ 검증 통과</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="invalid-badge">❌ 검증 실패</span>', unsafe_allow_html=True)
                for err in vr.get("errors", []):
                    st.error(f"• {err}")
            for warn in vr.get("warnings", []):
                st.warning(f"• {warn}")

# 대화 입력
st.divider()
col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.chat_input("메시지를 입력하세요... (예: 주간 운동 루틴 만들어줘)")

if user_input:
    if not api_client.verify_token():
        st.error("세션이 만료되었습니다. 다시 로그인해주세요.")
        st.stop()

    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 이전 대화 이력 (최근 10개)
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ][-10:]

    with st.spinner("에이전트가 분석 중입니다..."):
        result = api_client.chat(
            message=user_input,
            user_profile=st.session_state.user_profile,
            gym_data=st.session_state.gym_data,
            conversation_history=history,
        )

    if result and "error" not in result:
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("reply", ""),
            "extra": {
                "tool_calls_made": result.get("tool_calls_made", []),
                "curriculum": result.get("curriculum"),
                "validation_result": result.get("validation_result"),
                "complete": result.get("complete", False),
            },
        })
    else:
        error_msg = result.get("error", "알 수 없는 오류") if result else "응답 없음"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"오류가 발생했습니다: {error_msg}",
            "extra": {},
        })

    st.rerun()
