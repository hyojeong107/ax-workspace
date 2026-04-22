"""
오늘의 루틴 추천 페이지
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import json

from modules.recommender import recommend_routine, get_today_routine
from streamlit_app.components import (
    render_exercise_card,
    render_advice_card,
    render_section_header,
    render_page_title,
    render_badge,
    render_empty_state,
    render_divider,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _load_existing_routine(user_id: int):
    """오늘 이미 생성된 루틴이 있으면 캐시에서 반환."""
    existing = get_today_routine(user_id)
    if existing:
        return {
            "routine_id": existing["id"],
            "exercises":  json.loads(existing["exercises_json"]),
            "advice":     existing["ai_advice"],
        }
    return None


CATEGORY_ICONS = {
    "가슴":   "💪",
    "등":     "🦾",
    "하체":   "🦵",
    "어깨":   "🏋️",
    "팔":     "💪",
    "복근":   "🔥",
    "유산소": "🏃",
}


# ── 렌더 함수 ─────────────────────────────────────────────────────────────────

def render_routine(user_id: int, user: dict):
    render_page_title("오늘의 루틴", "🏋️", "AI가 분석한 맞춤 운동 프로그램")

    # 이미 생성된 루틴 확인
    existing = _load_existing_routine(user_id)

    if existing:
        st.markdown(
            '<div style="background:#FFF0EB;border:2px solid #FF4500;'
            'border-radius:10px;padding:10px 16px;margin-bottom:1.5rem;'
            'color:#FF4500;font-size:0.85rem;font-weight:700;box-shadow:3px 3px 0 #FF4500;">'
            '✓ 오늘 루틴이 이미 생성되어 있습니다. 아래에서 확인하세요.</div>',
            unsafe_allow_html=True,
        )
        _render_routine_content(existing)

        render_divider()
        col_btn, _ = st.columns([2, 5])
        with col_btn:
            if st.button("🔄 루틴 새로 생성", key="regen_btn"):
                st.info("오늘 루틴이 이미 있습니다. 내일 다시 생성할 수 있습니다.")
        return

    # 루틴 생성 버튼
    st.markdown(
        '<div style="background:#FFFFFF;border:2px solid #1A1A1A;border-radius:12px;'
        'padding:28px 24px;margin-bottom:1.5rem;text-align:center;box-shadow:4px 4px 0 #1A1A1A;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="color:#888888;font-size:0.9rem;margin-bottom:1rem;font-weight:500;">'
        'AI가 당신의 체력 수준·목표·성장 이력을 분석해 오늘에 딱 맞는 루틴을 만들어드립니다.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    col_btn, _ = st.columns([2, 5])
    with col_btn:
        generate_clicked = st.button("✨ 오늘 루틴 생성하기", key="gen_btn")

    if generate_clicked:
        with st.spinner("AI가 루틴을 생성 중입니다..."):
            result = recommend_routine(user)
        st.session_state["today_routine"] = result
        st.rerun()

    # session_state에 루틴이 있으면 표시
    if "today_routine" in st.session_state:
        _render_routine_content(st.session_state["today_routine"])


def _render_routine_content(result: dict):
    exercises = result["exercises"]
    advice    = result["advice"]

    # 조언 카드
    render_advice_card(advice)

    render_section_header("운동 목록", f"총 {len(exercises)}개 운동")

    # 운동 카드 2열 그리드
    for i in range(0, len(exercises), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(exercises):
                break
            ex = exercises[idx]
            weight = ex.get("weight_kg", 0)
            icon = CATEGORY_ICONS.get(ex.get("category", ""), "🏃")
            with col:
                render_exercise_card(
                    name=f"{icon} {ex.get('name', '')}",
                    sets=ex.get("sets", 0),
                    reps=ex.get("reps", 0),
                    weight_kg=float(weight),
                    category=ex.get("category", ""),
                    tip=ex.get("tip", ""),
                )

    # 요약 통계 바
    render_divider()
    render_section_header("루틴 요약")

    total_sets   = sum(ex.get("sets", 0) for ex in exercises)
    total_volume = sum(
        ex.get("sets", 0) * ex.get("reps", 0) * float(ex.get("weight_kg", 0) or 0)
        for ex in exercises
    )
    categories = list(dict.fromkeys(ex.get("category", "") for ex in exercises if ex.get("category")))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="fs-card" style="text-align:center;">'
            f'<div style="color:#888888;font-size:0.72rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;font-weight:700;">총 세트</div>'
            f'<div style="color:#FF4500;font-size:2rem;font-weight:800;'
            f'font-family:\'Space Grotesk\',sans-serif;">{total_sets}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="fs-card" style="text-align:center;">'
            f'<div style="color:#888888;font-size:0.72rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;font-weight:700;">총 볼륨</div>'
            f'<div style="color:#FF4500;font-size:2rem;font-weight:800;'
            f'font-family:\'Space Grotesk\',sans-serif;">{int(total_volume):,}</div>'
            f'<div style="color:#888888;font-size:0.75rem;">kg·rep</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="fs-card" style="text-align:center;">'
            f'<div style="color:#888888;font-size:0.72rem;text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;font-weight:700;">운동 부위</div>'
            f'<div style="color:#1A1A1A;font-size:1.1rem;font-weight:800;">'
            f'{" · ".join(categories[:3])}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
