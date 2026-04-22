"""
FitStep Streamlit Web App — 메인 진입점

실행 방법:
    cd 06_FitStep
    streamlit run streamlit_app/app.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

# ── 페이지 기본 설정 (반드시 가장 먼저 호출) ──────────────────────────────────
st.set_page_config(
    page_title="FitStep — AI 헬스 코치",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

from db.database import init_db
from db.user_repo import get_user
from streamlit_app.components import inject_global_css
from streamlit_app.pages.dashboard   import render_dashboard
from streamlit_app.pages.routine     import render_routine
from streamlit_app.pages.workout_log import render_workout_log
from streamlit_app.pages.gym_setup   import render_gym_setup
from streamlit_app.pages.user_setup  import render_user_select


# ── DB 초기화 (최초 1회) ──────────────────────────────────────────────────────
@st.cache_resource
def _init():
    init_db()

_init()


# ── 전역 CSS 주입 ─────────────────────────────────────────────────────────────
inject_global_css()


# ── 사이드바 ──────────────────────────────────────────────────────────────────

def _render_sidebar():
    with st.sidebar:
        # 로고 / 앱 이름
        st.markdown("""
        <div style="padding:1.5rem 1rem 1.2rem;">
          <div style="font-size:1.6rem;font-weight:800;color:#FFFFFF;
                      font-family:'Space Grotesk',sans-serif;letter-spacing:-0.02em;">
            💪 FitStep
          </div>
          <div style="color:#888888;font-size:0.75rem;margin-top:3px;font-weight:500;">AI 헬스 코치</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<hr style="border:none;border-top:1px solid #333;margin:0 0 1rem;">', unsafe_allow_html=True)

        # 로그인된 사용자 정보
        user_id   = st.session_state.get("user_id")
        user_name = st.session_state.get("user_name", "")

        if user_id:
            st.markdown(
                f'<div style="background:rgba(255,69,0,0.12);border:1px solid rgba(255,69,0,0.3);'
                f'border-radius:8px;padding:10px 14px;margin-bottom:1rem;">'
                f'<div style="color:#888888;font-size:0.68rem;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:0.08em;margin-bottom:3px;">현재 사용자</div>'
                f'<div style="color:#FFFFFF;font-weight:700;font-size:0.92rem;">{user_name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # 네비게이션
        NAV_ITEMS = {
            "dashboard":   ("📊", "대시보드"),
            "routine":     ("🏋️", "오늘의 루틴"),
            "workout_log": ("📋", "운동 기록"),
            "gym_setup":   ("🏢", "헬스장 설정"),
            "user_select": ("👤", "사용자 관리"),
        }

        current_page = st.session_state.get("page", "user_select" if not user_id else "dashboard")

        for key, (icon, label) in NAV_ITEMS.items():
            is_active = current_page == key
            if is_active:
                st.markdown(
                    f'<div style="background:#FF4500;border-radius:8px;padding:10px 14px;'
                    f'margin-bottom:4px;font-size:0.88rem;font-weight:700;color:#FFFFFF;">'
                    f'{icon} &nbsp; {label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"{icon}  {label}", key=f"nav_{key}", use_container_width=True):
                    if not user_id and key not in ("user_select",):
                        st.warning("먼저 사용자를 선택해주세요.")
                    else:
                        st.session_state["page"] = key
                        st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #333;margin:1.2rem 0 0.8rem;">', unsafe_allow_html=True)

        # 사용자 전환 버튼
        if user_id:
            if st.button("🔄  사용자 전환", use_container_width=True, key="switch_user"):
                for k in ["user_id", "user_name", "user", "today_routine"]:
                    st.session_state.pop(k, None)
                st.session_state["page"] = "user_select"
                st.rerun()

        # 버전 정보
        st.markdown(
            '<div style="color:#444;font-size:0.7rem;text-align:center;margin-top:2rem;">v1.0.0</div>',
            unsafe_allow_html=True,
        )


# ── 메인 라우터 ───────────────────────────────────────────────────────────────

def _route():
    user_id   = st.session_state.get("user_id")
    page      = st.session_state.get("page", "user_select")

    # 사용자 미선택 시 강제 이동
    if not user_id and page != "user_select":
        page = "user_select"
        st.session_state["page"] = page

    # user 객체 동기화 (새로고침 후 세션에서 복원)
    if user_id and "user" not in st.session_state:
        try:
            st.session_state["user"] = dict(get_user(user_id))
            st.session_state["user_name"] = st.session_state["user"]["name"]
        except Exception:
            st.session_state.pop("user_id", None)
            page = "user_select"

    user      = st.session_state.get("user", {})
    user_name = st.session_state.get("user_name", "")

    if page == "user_select":
        render_user_select()
    elif page == "dashboard":
        render_dashboard(user_id, user_name)
    elif page == "routine":
        render_routine(user_id, user)
    elif page == "workout_log":
        render_workout_log(user_id)
    elif page == "gym_setup":
        render_gym_setup(user_id)
    else:
        render_dashboard(user_id, user_name)


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main():
    _render_sidebar()
    _route()


if __name__ == "__main__":
    main()
else:
    # streamlit run 명령으로 실행 시 모듈 레벨에서 호출
    main()
