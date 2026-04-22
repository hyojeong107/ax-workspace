"""
대시보드 페이지 — 운동 통계 및 성장 현황
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta

from db.database import get_connection
from modules.progression import get_overall_progress_summary, analyze_progression
from streamlit_app.components import (
    render_kpi_card,
    render_section_header,
    render_page_title,
    render_empty_state,
    render_divider,
    render_status_badge,
)

# ── Plotly 공통 레이아웃 ──────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(family="DM Sans, sans-serif", color="#1A1A1A"),
    margin=dict(l=16, r=16, t=32, b=16),
    colorway=["#FF4500", "#1A1A1A", "#FF7A50", "#FFAA80"],
    xaxis=dict(gridcolor="#F0EBE3", linecolor="#E8E0D8", tickfont=dict(color="#888888")),
    yaxis=dict(gridcolor="#F0EBE3", linecolor="#E8E0D8", tickfont=dict(color="#888888")),
)


# ── 데이터 조회 함수 ──────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def get_stats(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM routines WHERE user_id=%s AND is_completed=1",
        (user_id,)
    )
    completed_routines = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM workout_logs WHERE user_id=%s",
        (user_id,)
    )
    total_logs = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(DISTINCT DATE(logged_at)) AS cnt FROM workout_logs WHERE user_id=%s",
        (user_id,)
    )
    active_days = cursor.fetchone()["cnt"]

    # 주간 운동일 수 (최근 7일)
    cursor.execute(
        "SELECT COUNT(DISTINCT DATE(logged_at)) AS cnt FROM workout_logs "
        "WHERE user_id=%s AND logged_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        (user_id,)
    )
    week_days = cursor.fetchone()["cnt"]

    # 연속 운동일
    cursor.execute(
        "SELECT DISTINCT DATE(logged_at) AS d FROM workout_logs "
        "WHERE user_id=%s ORDER BY d DESC",
        (user_id,)
    )
    dates = [row["d"] for row in cursor.fetchall()]
    streak = 0
    if dates:
        today = date.today()
        for i, d in enumerate(dates):
            if d == today - timedelta(days=i):
                streak += 1
            else:
                break

    # 이번 주 전날과 비교 (delta 계산)
    cursor.execute(
        "SELECT COUNT(DISTINCT DATE(logged_at)) AS cnt FROM workout_logs "
        "WHERE user_id=%s AND logged_at >= DATE_SUB(NOW(), INTERVAL 14 DAY) "
        "AND logged_at < DATE_SUB(NOW(), INTERVAL 7 DAY)",
        (user_id,)
    )
    prev_week_days = cursor.fetchone()["cnt"]

    cursor.close()
    conn.close()

    week_delta_val = week_days - prev_week_days
    week_delta = f"+{week_delta_val}" if week_delta_val >= 0 else str(week_delta_val)

    return {
        "completed_routines": completed_routines,
        "total_logs":         total_logs,
        "active_days":        active_days,
        "streak":             streak,
        "week_days":          week_days,
        "week_delta":         week_delta,
    }


@st.cache_data(ttl=60)
def get_weekly_activity(user_id: int) -> pd.DataFrame:
    """최근 4주 일별 운동 횟수 데이터."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DATE(logged_at) AS day, COUNT(*) AS count
        FROM workout_logs
        WHERE user_id=%s AND logged_at >= DATE_SUB(NOW(), INTERVAL 28 DAY)
        GROUP BY day
        ORDER BY day
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return pd.DataFrame(columns=["day", "count"])

    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])

    # 빈 날짜 채우기
    all_days = pd.date_range(
        start=date.today() - timedelta(days=27),
        end=date.today(),
        freq="D"
    )
    df = df.set_index("day").reindex(all_days, fill_value=0).reset_index()
    df.columns = ["day", "count"]
    return df


@st.cache_data(ttl=60)
def get_weight_history(user_id: int, exercise_name: str) -> pd.DataFrame:
    """특정 운동의 무게 변화 히스토리."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DATE(logged_at) AS day, MAX(weight_kg) AS max_weight
        FROM workout_logs
        WHERE user_id=%s AND exercise_name=%s AND weight_kg > 0
        GROUP BY day
        ORDER BY day
    """, (user_id, exercise_name))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        return pd.DataFrame(columns=["day", "max_weight"])
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    return df


@st.cache_data(ttl=60)
def get_category_dist(user_id: int) -> pd.DataFrame:
    """부위별 운동 횟수 분포."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    # routines의 exercises_json을 파싱하는 대신 workout_logs 기준으로 집계
    cursor.execute("""
        SELECT exercise_name, COUNT(*) AS cnt
        FROM workout_logs
        WHERE user_id=%s
        GROUP BY exercise_name
        ORDER BY cnt DESC
        LIMIT 8
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        return pd.DataFrame(columns=["exercise_name", "cnt"])
    return pd.DataFrame(rows)


# ── 차트 렌더 함수 ────────────────────────────────────────────────────────────

def _render_activity_chart(df: pd.DataFrame):
    if df.empty or df["count"].sum() == 0:
        render_empty_state("아직 운동 기록이 없습니다.", "📊")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["day"],
        y=df["count"],
        marker=dict(
            color=df["count"],
            colorscale=[[0, "#FFD5C8"], [1, "#FF4500"]],
            showscale=False,
        ),
        hovertemplate="%{x|%m/%d}<br>%{y}회<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT, "height": 220, "bargap": 0.3, "showlegend": False}
    layout["xaxis"] = {**PLOTLY_LAYOUT["xaxis"], "tickformat": "%m/%d"}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_weight_chart(df: pd.DataFrame, exercise_name: str):
    if df.empty:
        render_empty_state(f"'{exercise_name}' 기록이 없습니다.", "📈")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["day"],
        y=df["max_weight"],
        mode="lines+markers",
        line=dict(color="#FF4500", width=2.5),
        marker=dict(color="#FF4500", size=7),
        fill="tozeroy",
        fillcolor="rgba(255,69,0,0.08)",
        hovertemplate="%{x|%m/%d}<br>%{y}kg<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=220,
        showlegend=False,
        yaxis_title="최대 무게 (kg)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_top_exercises_chart(df: pd.DataFrame):
    if df.empty:
        return

    fig = go.Figure(go.Bar(
        x=df["cnt"],
        y=df["exercise_name"],
        orientation="h",
        marker=dict(
            color=df["cnt"],
            colorscale=[[0, "#FFD5C8"], [0.5, "#FF7A50"], [1, "#FF4500"]],
            showscale=False,
        ),
        hovertemplate="%{y}<br>%{x}회<extra></extra>",
    ))
    layout = {**PLOTLY_LAYOUT, "height": 280, "showlegend": False, "xaxis_title": "수행 횟수"}
    layout["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "categoryorder": "total ascending"}
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── 성장 현황 테이블 ──────────────────────────────────────────────────────────

def _render_progression_table(user_id: int, summary: list):
    if not summary:
        render_empty_state("아직 분석할 기록이 없어요.", "📊")
        return

    for row in summary:
        prog = analyze_progression(user_id, row["exercise_name"])
        col_name, col_stat, col_status = st.columns([3, 4, 2])

        with col_name:
            st.markdown(
                f'<div style="color:#1A1A1A;font-weight:700;font-size:0.92rem;'
                f'padding:8px 0;">{row["exercise_name"]}</div>',
                unsafe_allow_html=True,
            )
        with col_stat:
            st.markdown(
                f'<div style="color:#888888;font-size:0.82rem;padding:8px 0;">'
                f'최고 {row["max_weight"]}kg &nbsp;·&nbsp; '
                f'최고 {row["max_reps"]}회 &nbsp;·&nbsp; '
                f'{row["total_sessions"]}세션</div>',
                unsafe_allow_html=True,
            )
        with col_status:
            render_status_badge(prog["ready_to_progress"])

        # 제안 텍스트
        st.markdown(
            f'<div style="color:#888888;font-size:0.78rem;'
            f'padding:0 0 10px 0;border-bottom:1px solid #E8E0D8;">'
            f'→ {prog["suggestion"]}</div>',
            unsafe_allow_html=True,
        )


# ── 메인 렌더 함수 ────────────────────────────────────────────────────────────

def render_dashboard(user_id: int, user_name: str):
    render_page_title("대시보드", "📊", f"{user_name}님의 운동 성장 현황")

    stats = get_stats(user_id)

    # ── KPI 카드 4개 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("완료한 루틴", str(stats["completed_routines"]), "", "🏆")
    with c2:
        render_kpi_card("총 운동 기록", str(stats["total_logs"]), "", "📋")
    with c3:
        render_kpi_card("운동한 날", str(stats["active_days"]), stats["week_delta"] + " 이번주", "📅")
    with c4:
        streak_val = f"{stats['streak']}일" if stats["streak"] > 0 else "0일"
        render_kpi_card("연속 운동", streak_val, "", "🔥")

    if stats["total_logs"] == 0:
        render_divider()
        render_empty_state(
            "아직 운동 기록이 없어요.\n루틴 추천을 받고 첫 운동을 시작해보세요! 💪",
            "🏋️"
        )
        return

    render_divider()

    # ── 활동 히트맵 + 상위 운동 ──
    render_section_header("활동 현황", "최근 4주 일별 운동 횟수")
    col_act, col_top = st.columns([3, 2])

    with col_act:
        st.markdown(
            '<div class="fs-card" style="padding:16px 20px;">',
            unsafe_allow_html=True,
        )
        df_activity = get_weekly_activity(user_id)
        _render_activity_chart(df_activity)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_top:
        st.markdown(
            '<div class="fs-card" style="padding:16px 20px;">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="color:#888888;font-size:0.75rem;font-weight:600;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px;">자주 한 운동 TOP 8</div>',
            unsafe_allow_html=True,
        )
        df_top = get_category_dist(user_id)
        _render_top_exercises_chart(df_top)
        st.markdown("</div>", unsafe_allow_html=True)

    render_divider()

    # ── 무게 성장 차트 ──
    render_section_header("무게 성장 추이", "운동 선택 → 무게 변화 추적")

    summary = get_overall_progress_summary(user_id)
    weighted_exercises = [
        r["exercise_name"] for r in summary
        if r["max_weight"] and float(r["max_weight"]) > 0
    ]

    if weighted_exercises:
        selected = st.selectbox(
            "운동 선택",
            options=weighted_exercises,
            label_visibility="collapsed",
        )
        st.markdown(
            '<div class="fs-card" style="padding:16px 20px;">',
            unsafe_allow_html=True,
        )
        df_weight = get_weight_history(user_id, selected)
        _render_weight_chart(df_weight, selected)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        render_empty_state("무게를 사용한 운동 기록이 없습니다.", "🏋️")

    render_divider()

    # ── 성장 현황 테이블 ──
    render_section_header("운동별 성장 현황", "레벨업 타이밍과 다음 목표")
    _render_progression_table(user_id, summary)
