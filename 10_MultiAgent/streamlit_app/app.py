"""FitStep Multi-Agent · Streamlit UI"""

import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv

_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"), override=True)

try:
    for _k in ["AGENT_API_URL", "JWT_SECRET_KEY"]:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

sys.path.insert(0, _HERE)
import api_client

st.set_page_config(
    page_title="FitStep · Multi-Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.agent-bubble { background:#f0f4ff; border-radius:12px; padding:12px 16px; margin:8px 0; }
.user-bubble  { background:#e8f5e9; border-radius:12px; padding:12px 16px; margin:8px 0; text-align:right; }
.specialist-tag { display:inline-block; border-radius:6px; padding:2px 10px; font-size:0.78rem; margin:2px; font-weight:bold; }
.tag-strength { background:#fff3e0; color:#e65100; }
.tag-cardio   { background:#e3f2fd; color:#1565c0; }
.tag-rehab    { background:#f3e5f5; color:#6a1b9a; }
.pipeline-step { font-size:0.82rem; color:#555; margin:2px 0; padding-left:8px; border-left:3px solid #6c63ff; }
.valid-badge   { color:#2e7d32; font-weight:bold; }
.invalid-badge { color:#c62828; font-weight:bold; }
.curriculum-card { background:#fff8e1; border-left:4px solid #ffc107; border-radius:8px; padding:12px 16px; margin:8px 0; }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────────
for key, default in [
    ("logged_in", False), ("token", None),
    ("messages", []), ("user_profile", None), ("gym_data", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 FitStep Multi-Agent")
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
                st.error("로그인 실패")
    else:
        st.success("✅ 로그인됨")
        if st.button("로그아웃", use_container_width=True):
            for k in ("logged_in", "token", "messages"):
                st.session_state[k] = False if k == "logged_in" else None if k == "token" else []
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

            fitness_level = st.selectbox("체력 수준", ["초급", "중급", "고급"])
            goal = st.text_input("운동 목표", placeholder="예: 체중 감량, 근육 증가")
            injury = st.text_area("부상/특이사항", height=60, placeholder="예: 허리 디스크, 무릎 통증")
            st.caption(f"BMI: {bmi} ({_bmi_grade(bmi)})")

            if st.form_submit_button("프로필 저장"):
                st.session_state.user_profile = {
                    "age": age, "gender": gender,
                    "height_cm": height, "weight_kg": weight,
                    "bmi": bmi, "bmi_grade": _bmi_grade(bmi),
                    "age_group": f"{(age // 10) * 10}대",
                    "fitness_level": fitness_level,
                    "goal": goal, "injury_tags": injury,
                }
                st.success("프로필 저장됨!")

        st.divider()
        st.subheader("헬스장 기구")
        gym_input = st.text_area(
            "보유 기구 목록 (쉼표 구분)",
            placeholder="예: 바벨, 덤벨, 트레드밀, 풀업바",
            height=80,
        )
        if st.button("기구 저장"):
            if gym_input.strip():
                equipment = [e.strip() for e in gym_input.split(",") if e.strip()]
                st.session_state.gym_data = {"equipment": equipment}
                st.success(f"{len(equipment)}개 기구 저장됨!")

        st.divider()
        # 커리큘럼 이력
        st.subheader("📂 커리큘럼 이력")
        if st.button("이력 불러오기", use_container_width=True):
            data = api_client.list_curricula()
            if data:
                st.session_state["curricula_list"] = data

        curricula_data = st.session_state.get("curricula_list")
        if curricula_data:
            items = curricula_data.get("items", [])
            st.caption(f"총 {curricula_data.get('total', 0)}개")
            for item in items:
                col1, col2 = st.columns([3, 1])
                with col1:
                    label = item.get("label") or f"커리큘럼 #{item['id']}"
                    specialists = ", ".join(item.get("specialists_used", []))
                    valid_icon = "✅" if item.get("is_valid") else "❌"
                    st.markdown(
                        f"**{label}** {valid_icon}  \n"
                        f"<small>{item['created_at'][:16]} | {item['total_days']}일 | {specialists}</small>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    dl_url = api_client.download_curriculum_url(item["id"])
                    st.markdown(f"[⬇]({dl_url})", unsafe_allow_html=True)


# ── 메인 화면 ─────────────────────────────────────────────────────────────────
st.title("🤖 FitStep Multi-Agent")
st.caption("근력 · 유산소 · 재활 전문 에이전트가 협력하여 맞춤형 운동 커리큘럼을 생성합니다.")

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
        st.markdown(f'<div class="agent-bubble">🤖 에이전트 처리 완료</div>', unsafe_allow_html=True)

        # 전문가 태그
        sp = extra.get("specialists_called", {})
        if sp:
            tags = ""
            if sp.get("strength"):
                tags += '<span class="specialist-tag tag-strength">💪 근력</span>'
            if sp.get("cardio"):
                tags += '<span class="specialist-tag tag-cardio">🏃 유산소</span>'
            if sp.get("rehab"):
                tags += '<span class="specialist-tag tag-rehab">🩺 재활</span>'
            if tags:
                reason = sp.get("reason", "")
                st.markdown(f"<div>{tags}<small style='color:#888'> — {reason}</small></div>", unsafe_allow_html=True)

        # 기구 매칭 결과
        matched = extra.get("matched_exercises", {})
        if matched:
            mode = matched.get("mode", "")
            if mode == "llm_fallback":
                st.warning("⚠️ 기구 데이터 없음 — 맨몸 운동 위주로 생성됨")
            elif mode == "filtered":
                st.info(f"🏋️ {matched.get('message', '')}")

        # 파이프라인 로그 (검증 실패 경고 강조)
        pipeline_log = extra.get("pipeline_log", [])
        if pipeline_log:
            with st.expander("⚙️ 파이프라인 처리 로그", expanded=False):
                for log in pipeline_log:
                    if "❌" in log or "실패" in log:
                        st.error(f"🔴 {log}")
                    elif "✅" in log or "완료" in log:
                        st.success(f"🟢 {log}")
                    else:
                        st.markdown(f'<div class="pipeline-step">▸ {log}</div>', unsafe_allow_html=True)

        # 검증 결과 (내부 검증 실패 경고 강조)
        vr = extra.get("validation_result")
        if vr:
            if vr.get("is_valid"):
                st.markdown('<span class="valid-badge">✅ 커리큘럼 검증 통과</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="invalid-badge">❌ 커리큘럼 검증 실패</span>', unsafe_allow_html=True)
                for err in vr.get("errors", []):
                    st.error(f"• {err}")
            for warn in vr.get("warnings", []):
                st.warning(f"• {warn}")
            # check_summary 표시
            check_summary = vr.get("check_summary", {})
            if check_summary:
                with st.expander("🔍 검증 항목 상세", expanded=False):
                    for check_name, passed in check_summary.items():
                        icon = "✅" if passed else "❌"
                        st.markdown(f"{icon} `{check_name}`")

        # 커리큘럼 표시
        curriculum = extra.get("curriculum")
        if curriculum and "error" not in curriculum:
            with st.expander("📋 생성된 커리큘럼 보기", expanded=True):
                specialists_used = curriculum.get("specialists_used", [])
                if specialists_used:
                    st.caption(f"참여 전문가: {', '.join(specialists_used)}")

                summary = curriculum.get("summary", "")
                if summary:
                    st.markdown(f"**요약:** {summary}")

                weekly_plan = curriculum.get("weekly_plan", [])
                for session in weekly_plan:
                    session_type = session.get("type", "")
                    type_icon = {"strength": "💪", "cardio": "🏃", "rehab": "🩺"}.get(session_type, "📌")
                    st.markdown(
                        f"**{type_icon} {session.get('day', '')} — {session.get('focus', '')}** "
                        f"({session.get('duration_minutes', 0)}분)"
                    )
                    hr_zone = session.get("heart_rate_zone")
                    if hr_zone:
                        st.caption(f"심박수 존: {hr_zone}")
                    for ex in session.get("exercises", []):
                        reps = ex.get("reps", "")
                        rest = ex.get("rest_seconds", 0)
                        note = ex.get("notes", "")
                        line = f"  - {ex.get('name', '')} {ex.get('sets', 0)}세트 × {reps}회, 휴식 {rest}초"
                        if note:
                            line += f" *(주의: {note})*"
                        st.markdown(line)

                notes = curriculum.get("notes", "")
                if notes:
                    st.info(f"📌 {notes}")

                st.download_button(
                    "⬇ JSON 다운로드",
                    data=json.dumps(curriculum, ensure_ascii=False, indent=2),
                    file_name="curriculum.json",
                    mime="application/json",
                )

# 입력
st.divider()
user_input = st.chat_input("메시지를 입력하세요... (예: 주간 운동 루틴 만들어줘)")

if user_input:
    if not api_client.verify_token():
        st.error("세션이 만료되었습니다. 다시 로그인해주세요.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("멀티에이전트가 분석 중입니다... (근력/유산소/재활 전문가 협의)"):
        result = api_client.chat(
            message=user_input,
            user_profile=st.session_state.user_profile,
            gym_data=st.session_state.gym_data,
        )

    if result and "error" not in result:
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("reply", ""),
            "extra": {
                "pipeline_log": result.get("pipeline_log", []),
                "curriculum": result.get("curriculum"),
                "validation_result": result.get("validation_result"),
                "matched_exercises": result.get("matched_exercises"),
                "specialists_called": result.get("specialists_called"),
                "complete": result.get("complete", False),
            },
        })
    else:
        error_msg = result.get("error", "알 수 없는 오류") if result else "응답 없음"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"오류: {error_msg}",
            "extra": {},
        })

    st.rerun()
