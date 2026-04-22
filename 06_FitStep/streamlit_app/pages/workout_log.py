"""
운동 기록 페이지 — 루틴별 완료 기록 입력 및 히스토리 조회
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import json
import pandas as pd

from db.database import get_connection
from modules.recommender import get_today_routine
from modules.workout_logger import save_log, mark_routine_complete, get_logged_exercises
from streamlit_app.components import (
    render_section_header,
    render_page_title,
    render_progress_bar,
    render_empty_state,
    render_divider,
    render_badge,
)


# ── 데이터 조회 ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _get_recent_logs(user_id: int, limit: int = 50) -> list:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name, sets_done, reps_done, weight_kg, note,
               DATE(logged_at) AS log_date, logged_at
        FROM workout_logs
        WHERE user_id=%s
        ORDER BY logged_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


# ── 기록 입력 폼 ──────────────────────────────────────────────────────────────

def _render_log_form(user_id: int, routine: dict):
    """루틴의 각 운동에 대한 기록 입력 폼을 렌더링합니다."""
    exercises    = routine["exercises"]
    routine_id   = routine["routine_id"]
    already_done = set(get_logged_exercises(routine_id))
    todo         = [ex for ex in exercises if ex["name"] not in already_done]

    done_count = len(already_done)
    total      = len(exercises)

    render_progress_bar("오늘 루틴 진행도", done_count, total, "개")

    if not todo:
        st.markdown(
            '<div style="background:#FFF0EB;border:2px solid #FF4500;'
            'border-radius:12px;padding:20px;text-align:center;margin:1rem 0;'
            'box-shadow:4px 4px 0 #FF4500;">'
            '<div style="font-size:2rem;margin-bottom:8px;">🎉</div>'
            '<div style="color:#FF4500;font-weight:800;font-size:1rem;">오늘 루틴 완료!</div>'
            '<div style="color:#888888;font-size:0.85rem;margin-top:4px;">수고하셨습니다!</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div style="color:#888888;font-size:0.85rem;margin-bottom:1.2rem;font-weight:500;">'
        f'남은 운동 <span style="color:#FF4500;font-weight:800;">{len(todo)}</span>개</div>',
        unsafe_allow_html=True,
    )

    for ex in todo:
        ex_name = ex["name"]
        with st.expander(f"📝 {ex_name}", expanded=True):
            st.markdown(
                f'<div style="background:#F5F0EB;border:2px solid #1A1A1A;border-radius:8px;padding:10px 14px;'
                f'margin-bottom:12px;display:flex;gap:16px;">'
                f'<span style="color:#888888;font-size:0.8rem;font-weight:500;">'
                f'목표: <b style="color:#1A1A1A;">{ex.get("sets","-")}세트 × {ex.get("reps","-")}회</b>'
                f' &nbsp;|&nbsp; 권장무게: <b style="color:#FF4500;">{ex.get("weight_kg",0)}kg</b>'
                f'</span></div>',
                unsafe_allow_html=True,
            )
            if ex.get("tip"):
                st.markdown(
                    f'<div style="color:#888888;font-size:0.8rem;'
                    f'border-left:3px solid #FF4500;padding-left:10px;margin-bottom:12px;font-weight:500;">'
                    f'💡 {ex["tip"]}</div>',
                    unsafe_allow_html=True,
                )

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                sets_done = st.number_input(
                    "세트 수", min_value=0, max_value=20,
                    value=int(ex.get("sets", 3)),
                    key=f"sets_{ex_name}",
                )
            with col_b:
                reps_done = st.number_input(
                    "반복 수", min_value=0, max_value=100,
                    value=int(ex.get("reps", 10)),
                    key=f"reps_{ex_name}",
                )
            with col_c:
                weight_done = st.number_input(
                    "무게(kg)", min_value=0.0, max_value=500.0, step=0.5,
                    value=float(ex.get("weight_kg", 0) or 0),
                    key=f"weight_{ex_name}",
                )

            note = st.text_input("메모 (선택)", key=f"note_{ex_name}", placeholder="예: 마지막 세트 힘들었음")

            col_save, col_skip = st.columns([2, 1])
            with col_save:
                if st.button(f"✓ 기록 저장", key=f"save_{ex_name}"):
                    save_log(user_id, routine_id, ex_name,
                             sets_done, reps_done, weight_done, note)
                    st.success(f"{ex_name} 기록 완료!")
                    # 전체 완료 체크
                    all_names    = {e["name"] for e in exercises}
                    done_after   = set(get_logged_exercises(routine_id))
                    if all_names <= done_after:
                        mark_routine_complete(routine_id)
                    st.cache_data.clear()
                    st.rerun()
            with col_skip:
                if st.button("건너뛰기", key=f"skip_{ex_name}"):
                    st.rerun()


# ── 히스토리 테이블 ───────────────────────────────────────────────────────────

def _render_history(user_id: int):
    render_section_header("운동 기록 히스토리", "최근 50개 기록")

    logs = _get_recent_logs(user_id)
    if not logs:
        render_empty_state("아직 운동 기록이 없습니다.", "📋")
        return

    df = pd.DataFrame(logs)
    df = df.rename(columns={
        "log_date":     "날짜",
        "exercise_name":"운동명",
        "sets_done":    "세트",
        "reps_done":    "횟수",
        "weight_kg":    "무게(kg)",
        "note":         "메모",
    })
    df = df[["날짜", "운동명", "세트", "횟수", "무게(kg)", "메모"]]
    df["메모"] = df["메모"].fillna("-")

    # 커스텀 스타일 테이블
    st.markdown(
        '<div style="background:#FFFFFF;border:2px solid #1A1A1A;border-radius:12px;'
        'overflow:hidden;padding:0;box-shadow:4px 4px 0 #1A1A1A;">',
        unsafe_allow_html=True,
    )
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "날짜":     st.column_config.DateColumn("날짜", format="YYYY-MM-DD"),
            "무게(kg)": st.column_config.NumberColumn("무게(kg)", format="%.1f kg"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ── 메인 렌더 함수 ────────────────────────────────────────────────────────────

def render_workout_log(user_id: int):
    render_page_title("운동 기록", "📋", "오늘 루틴 완료 기록 및 히스토리")

    tab_log, tab_history = st.tabs(["📝 오늘 기록하기", "📊 히스토리"])

    with tab_log:
        today_routine = get_today_routine(user_id)

        if not today_routine:
            render_empty_state(
                "오늘 생성된 루틴이 없습니다.\n'오늘의 루틴' 메뉴에서 먼저 루틴을 생성해주세요.",
                "🏋️"
            )
            return

        routine_data = {
            "routine_id": today_routine["id"],
            "exercises":  json.loads(today_routine["exercises_json"]),
            "advice":     today_routine["ai_advice"],
        }

        render_section_header("오늘 루틴", "각 운동을 완료하고 결과를 입력해주세요")
        _render_log_form(user_id, routine_data)

    with tab_history:
        _render_history(user_id)
