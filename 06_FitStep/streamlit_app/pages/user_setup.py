"""
사용자 프로필 페이지 — 신규 생성 및 기존 프로필 선택
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from db.user_repo import save_user, get_all_users, get_user
from streamlit_app.components import (
    render_page_title,
    render_section_header,
    render_divider,
    render_empty_state,
)

GENDER_MAP      = {"남성": "male", "여성": "female", "기타": "other"}
FITNESS_MAP     = {"초보자": "beginner", "중급자": "intermediate", "고급자": "advanced"}
FITNESS_LABELS  = {"beginner": "초보자", "intermediate": "중급자", "advanced": "고급자"}
GOAL_OPTIONS    = ["체중 감량", "근육 증가", "체력 향상", "건강 유지", "재활 / 부상 회복"]


# ── 프로필 카드 ───────────────────────────────────────────────────────────────

def _render_profile_card(user: dict, is_selected: bool = False):
    border = "#FF4500" if is_selected else "#1A1A1A"
    shadow = "4px 4px 0 #FF4500" if is_selected else "4px 4px 0 #1A1A1A"
    bmi = round(user["weight_kg"] / ((user["height_cm"] / 100) ** 2), 1) if user.get("height_cm") and user.get("weight_kg") else "-"
    level_label = FITNESS_LABELS.get(user.get("fitness_level", ""), user.get("fitness_level", ""))
    gender_map = {"male": "남성", "female": "여성", "other": "기타"}
    gender_label = gender_map.get(user.get("gender", ""), "-")
    health = user.get("health_notes", "")
    health_html = (
        f'<div style="color:#FF4500;font-size:0.78rem;margin-top:4px;font-weight:600;">⚠ {health}</div>'
        if health and health != "없음" else ""
    )

    st.markdown(
        f'<div class="fs-card" style="border-color:{border};box-shadow:{shadow};">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div>'
        f'<div style="font-size:1.1rem;font-weight:800;color:#1A1A1A;margin-bottom:4px;">{user["name"]}</div>'
        f'<div style="color:#888888;font-size:0.82rem;font-weight:500;">{user.get("age","?")}세 &nbsp;·&nbsp; '
        f'{gender_label} &nbsp;·&nbsp; BMI {bmi}</div>'
        f'</div>'
        f'<span style="background:#FF4500;color:#FFFFFF;border:2px solid #1A1A1A;'
        f'border-radius:6px;padding:3px 10px;font-size:0.72rem;font-weight:700;'
        f'box-shadow:2px 2px 0 #1A1A1A;">{level_label}</span>'
        f'</div>'
        f'<div style="margin-top:10px;color:#888888;font-size:0.82rem;font-weight:500;">'
        f'🎯 {user.get("goal","")}</div>'
        f'{health_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── 프로필 선택 ───────────────────────────────────────────────────────────────

def render_user_select():
    """기존 사용자 선택 또는 신규 생성 화면."""
    render_page_title("사용자 선택", "👤", "기존 프로필을 선택하거나 새로 만드세요")

    users = get_all_users()

    tab_select, tab_new = st.tabs(["기존 프로필 선택", "새 프로필 만들기"])

    with tab_select:
        if not users:
            render_empty_state("저장된 프로필이 없습니다.\n'새 프로필 만들기'에서 시작해보세요!", "👤")
        else:
            st.markdown(
                '<div style="color:#888888;font-size:0.85rem;margin-bottom:1rem;font-weight:500;">'
                '프로필을 선택하면 해당 사용자로 시작합니다.</div>',
                unsafe_allow_html=True,
            )
            current_id = st.session_state.get("user_id")

            for user in users:
                col_card, col_btn = st.columns([5, 1])
                with col_card:
                    _render_profile_card(dict(user), is_selected=(user["id"] == current_id))
                with col_btn:
                    st.markdown("<div style='padding-top:16px;'>", unsafe_allow_html=True)
                    if st.button("선택", key=f"sel_{user['id']}"):
                        st.session_state["user_id"]   = user["id"]
                        st.session_state["user_name"] = user["name"]
                        st.session_state["user"]      = dict(user)
                        st.session_state["page"]      = "dashboard"
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    with tab_new:
        render_section_header("새 프로필 등록", "건강 정보를 입력하면 AI가 최적화된 루틴을 추천합니다")
        _render_new_user_form()


def _render_new_user_form():
    """신규 사용자 입력 폼."""
    with st.form("new_user_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("이름 *", placeholder="홍길동")
            age  = st.number_input("나이 *", min_value=10, max_value=100, value=25)
        with c2:
            gender       = st.selectbox("성별 *", ["남성", "여성", "기타"])
            fitness_level = st.selectbox("체력 수준 *", ["초보자", "중급자", "고급자"])

        render_divider()

        c3, c4 = st.columns(2)
        with c3:
            height_cm = st.number_input("키 (cm) *", min_value=100.0, max_value=250.0,
                                        value=170.0, step=0.5)
        with c4:
            weight_kg = st.number_input("몸무게 (kg) *", min_value=30.0, max_value=200.0,
                                        value=65.0, step=0.5)

        render_divider()

        goals = st.multiselect(
            "운동 목표 * (복수 선택 가능)",
            GOAL_OPTIONS,
            default=["체중 감량"],
        )

        health_notes = st.text_area(
            "건강 주의사항",
            placeholder="부상 이력, 못 하는 운동 등 (없으면 비워두세요)",
            height=80,
        )

        submitted = st.form_submit_button("프로필 저장", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("이름을 입력해주세요.")
            return
        if not goals:
            st.error("운동 목표를 1개 이상 선택해주세요.")
            return

        goal_str  = ", ".join(goals)
        notes_str = health_notes.strip() or "없음"

        user_id = save_user(
            name.strip(), int(age), GENDER_MAP[gender],
            float(height_cm), float(weight_kg),
            FITNESS_MAP[fitness_level], goal_str, notes_str,
        )

        user = dict(get_user(user_id))
        st.session_state["user_id"]   = user_id
        st.session_state["user_name"] = user["name"]
        st.session_state["user"]      = user
        st.session_state["page"]      = "dashboard"

        st.success(f"✓ '{name}' 프로필이 저장되었습니다! 대시보드로 이동합니다.")
        st.rerun()
