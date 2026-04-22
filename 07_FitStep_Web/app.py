"""
FitStep · Streamlit Web App
나만의 AI 헬스 코치  —  Black & White Design
"""

import streamlit as st
import sys
import os

# ── .env 로드 (로컬 개발용) ───────────────────────────────────────────────────
from dotenv import load_dotenv
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, ".env"), override=True)
# 06_FitStep/.env 도 로드 (gym_rag 모듈이 RAG_API_URL을 여기서 읽음)
load_dotenv(os.path.join(_HERE, "..", "06_FitStep", ".env"), override=False)

# ── Secrets → env vars (Streamlit Cloud) ─────────────────────────────────────
_SECRET_KEYS = ["RAG_API_URL", "RAG_API_KEY"]
try:
    for _k in _SECRET_KEYS:
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

import json
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# ── Path Setup (RAG 모듈만 사용) ──────────────────────────────────────────────
_FITSTEP = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "06_FitStep")
)
sys.path.insert(0, _FITSTEP)
os.chdir(_FITSTEP)

# ── API Client (DB + RAG 모두 FastAPI 경유) ───────────────────────────────────
_STREAMLIT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _STREAMLIT_DIR)
from api_client import (
    api_save_user, api_login,
    api_username_exists,
    api_save_routine, api_get_today_routine, api_complete_routine, api_delete_today_routine,
    api_save_log, api_get_logged_names, api_get_recent_logs,
    api_get_recent_exercises, api_get_stats, api_get_progression,
    api_get_exercise_history, api_get_exercise_gif, api_get_exercise_list
)
from rag.gym_rag import has_gym_data, save_gym_to_vector_db, get_gym_profile_from_api

# ── Cached API wrappers (Streamlit 리런마다 재호출 방지) ──────────────────────
@st.cache_data(ttl=3600)
def _cached_exercise_list():
    return api_get_exercise_list()

@st.cache_data(ttl=300)
def _cached_stats(user_id: int):
    return api_get_stats(user_id)

@st.cache_data(ttl=60)
def _cached_has_gym_data(user_id: int):
    return has_gym_data(user_id)

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitStep · AI 헬스 코치",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS (테마 파일에서 로드) ──────────────────────────────────────────
# .env에서 못 읽는 경우 대비해 직접 재로드
load_dotenv(os.path.join(_HERE, ".env"), override=True)
_THEME = os.getenv("FITSTEP_THEME", "lavender")
print(f"[DEBUG] FITSTEP_THEME={_THEME}, _HERE={_HERE}")
_THEME_FILE = os.path.join(_HERE, "themes", f"{_THEME}.css")
try:
    with open(_THEME_FILE, encoding="utf-8") as _f:
        _css = _f.read()
except FileNotFoundError:
    with open(os.path.join(_HERE, "themes", "lavender.css"), encoding="utf-8") as _f:
        _css = _f.read()

st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

# ── Theme Colors (인라인 스타일용) ────────────────────────────────────────────
if _THEME == "health":
    _C = {
        "primary":    "#1c1c2e",
        "accent":     "#4ecb9e",
        "secondary":  "#2a9d74",
        "primary2":   "#2a9d74",
        "text_sub":   "#8a8fa8",
        "text_dim":   "#6b7280",
        "bg_card":    "#ffffff",
        "bg_light":   "#f4f5fb",
        "border":     "rgba(228,230,240,0.8)",
        "shadow":     "rgba(28,28,46,0.08)",
        "shadow2":    "rgba(28,28,46,0.12)",
        "chip_done_bg":    "#1c1c2e",
        "chip_cur_border": "#4ecb9e",
        "chip_cur_color":  "#1c1c2e",
        "chip_none_border":"rgba(212,214,224,0.6)",
        "chip_none_color": "#9b9bb8",
        "heat_high":  "#1c1c2e",
        "heat_low":   "#4ecb9e",
        "heat_none":  "rgba(28,28,46,0.08)",
        "heat_legend": "미활동 &nbsp; ■ 민트: 1–2회 &nbsp; ■ 다크: 3회 이상",
        "tip_bg":     "linear-gradient(135deg, rgba(78,203,158,0.13) 0%, rgba(42,157,116,0.10) 100%)",
        "tip_border": "#4ecb9e",
        "tip_label":  "#2a9d74",
        "goal_color": "#4ecb9e",
        "stat_grad":  "linear-gradient(135deg,#1c1c2e,#4ecb9e)",
        "reps_grad":  "linear-gradient(135deg,#2a9d74,#1a7a58)",
        "logo_grad":  "linear-gradient(135deg, #1c1c2e, #4ecb9e)",
        "header_grad":"linear-gradient(135deg, #1c1c2e, #4ecb9e)",
        "user_card_bg":"rgba(255,255,255,0.95)",
        "user_card_border":"rgba(228,230,240,0.8)",
        "user_avatar_grad":"linear-gradient(135deg, #1c1c2e, #4ecb9e)",
        "avatar_shadow":"rgba(28,28,46,0.2)",
        "bar_cs":     [[0,"#b8e8d8"],[0.5,"#4ecb9e"],[1,"#1c1c2e"]],
        "grid_color": "rgba(28,28,46,0.06)",
        "complete_bg":"linear-gradient(135deg, rgba(212,238,218,0.9), rgba(255,255,255,0.9))",
        "complete_border":"rgba(228,230,240,0.8)",
        "complete_shadow":"rgba(28,28,46,0.08)",
        "log_card_bg":"linear-gradient(135deg, rgba(212,238,218,0.6), rgba(255,255,255,0.8))",
        "badge_grad": "linear-gradient(135deg,#1c1c2e,#4ecb9e)",
        "badge_shadow":"rgba(28,28,46,0.2)",
    }
else:
    _C = {
        "primary":    "#2d2d6b",
        "accent":     "#7b68c8",
        "secondary":  "#4a3880",
        "primary2":   "#4a3880",
        "text_sub":   "#6b6b8a",
        "text_dim":   "#6b6b8a",
        "bg_card":    "rgba(255,255,255,0.65)",
        "bg_light":   "rgba(255,255,255,0.5)",
        "border":     "rgba(255,255,255,0.8)",
        "shadow":     "rgba(45,45,107,0.08)",
        "shadow2":    "rgba(45,45,107,0.12)",
        "chip_done_bg":    "linear-gradient(135deg,#2d2d6b,#7b68c8)",
        "chip_cur_border": "#7b68c8",
        "chip_cur_color":  "#2d2d6b",
        "chip_none_border":"rgba(123,104,200,0.2)",
        "chip_none_color": "#9b9bb8",
        "heat_high":  "#2d2d6b",
        "heat_low":   "#7b68c8",
        "heat_none":  "rgba(123,104,200,0.12)",
        "heat_legend": "미활동 &nbsp; ■ 연보라: 1–2회 &nbsp; ■ 진보라: 3회 이상",
        "tip_bg":     "linear-gradient(135deg, rgba(123,104,200,0.18) 0%, rgba(74,152,127,0.13) 100%)",
        "tip_border": "#7b68c8",
        "tip_label":  "#7b68c8",
        "goal_color": "#7b68c8",
        "stat_grad":  "linear-gradient(135deg,#2d2d6b,#7b68c8)",
        "reps_grad":  "linear-gradient(135deg,#4a9b7f,#2d7a60)",
        "logo_grad":  "linear-gradient(135deg, #2d2d6b, #7b68c8)",
        "header_grad":"linear-gradient(135deg, #2d2d6b, #7b68c8)",
        "user_card_bg":"rgba(255,255,255,0.6)",
        "user_card_border":"rgba(255,255,255,0.8)",
        "user_avatar_grad":"linear-gradient(135deg, #2d2d6b, #7b68c8)",
        "avatar_shadow":"rgba(45,45,107,0.3)",
        "bar_cs":     [[0,"#c8b8e8"],[0.5,"#7b68c8"],[1,"#2d2d6b"]],
        "grid_color": "rgba(123,104,200,0.12)",
        "complete_bg":"linear-gradient(135deg, rgba(232,228,248,0.8), rgba(212,238,218,0.8))",
        "complete_border":"rgba(255,255,255,0.8)",
        "complete_shadow":"rgba(45,45,107,0.12)",
        "log_card_bg":"linear-gradient(135deg, rgba(232,228,248,0.75), rgba(255,255,255,0.65))",
        "badge_grad": "linear-gradient(135deg,#2d2d6b,#7b68c8)",
        "badge_shadow":"rgba(45,45,107,0.25)",
    }

# ── Session State Init ─────────────────────────────────────────────────────────
_DEFAULTS = {
    "page": "login",
    "user_id": None,
    "user": None,
    "today_result": None,
    "log_index": 0,
    "creating_user": False,
    "gym_initialized": False,
    "gym_eq_list": [],
    "gym_name_edit": "",
    "gym_notes_edit": "",
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


# (DB init is handled by FastAPI startup)


# ── Navigation ────────────────────────────────────────────────────────────────
def nav(page: str):
    # gym page 나갈 때 초기화 플래그 리셋
    if st.session_state.page == "gym" and page != "gym":
        st.session_state.gym_initialized = False
    st.session_state.page = page
    st.rerun()


# ── UI Helpers ────────────────────────────────────────────────────────────────
def _header(title: str, subtitle: str = ""):
    st.markdown(
        f"<h1 style='margin-bottom:0; letter-spacing:-0.03em; background: {_C['header_grad']}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>{title}</h1>",
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(
            f"<p style='color:{_C['text_sub']}; margin-top:3px; font-size:0.95rem; font-weight:500'>{subtitle}</p>",
            unsafe_allow_html=True,
        )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)


def _back_btn(page="menu"):
    cols = st.columns([1, 5])
    with cols[0]:
        if st.button("← 메뉴"):
            nav(page)


def _badge(text: str, variant: str = "filled") -> str:
    cls = {"filled": "badge", "gray": "badge-gray", "outline": "badge-outline"}.get(
        variant, "badge"
    )
    return f"<span class='{cls}'>{text}</span>"


def _bw_layout() -> dict:
    return dict(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Inter, system-ui, sans-serif", color="#1a1a2e"),
        margin=dict(l=0, r=0, t=20, b=30),
        showlegend=False,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LOGIN / USER SELECTION
# ══════════════════════════════════════════════════════════════════════════════
def page_login():
    _, col, _ = st.columns([1, 1.8, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)

        # ── 로고 ──
        st.markdown(
            f"""
            <div style='text-align:center; padding:2rem 0 1.8rem'>
                <div style='width:72px; height:72px; background:{_C['logo_grad']};
                            border-radius:20px; display:flex; align-items:center; justify-content:center;
                            margin:0 auto 1rem; box-shadow:0 8px 24px {_C['avatar_shadow']}; font-size:2rem;'>💪</div>
                <h1 style='font-size:2.8rem; letter-spacing:-0.05em; margin:6px 0 0;
                           background:{_C['logo_grad']};
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>FitStep</h1>
                <p style='color:{_C['text_sub']}; margin:6px 0 0; font-size:0.95rem; font-weight:500'>나만의 AI 헬스 코치</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        if not st.session_state.creating_user:
            # ── 로그인 폼 ──
            with st.form("login_form"):
                st.markdown(
                    "<p style='font-size:0.85rem; color:#555; margin-bottom:0.2rem'>아이디</p>",
                    unsafe_allow_html=True,
                )
                login_id = st.text_input("아이디", placeholder="아이디를 입력하세요", label_visibility="collapsed")
                st.markdown(
                    "<p style='font-size:0.85rem; color:#555; margin:0.6rem 0 0.2rem'>비밀번호</p>",
                    unsafe_allow_html=True,
                )
                login_pw = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요", label_visibility="collapsed")
                login_btn = st.form_submit_button("로그인", use_container_width=True)

            if login_btn:
                if not login_id.strip() or not login_pw.strip():
                    st.error("아이디와 비밀번호를 모두 입력해주세요.")
                else:
                    user_row = api_login(login_id.strip(), login_pw)
                    if user_row:
                        st.session_state.user_id = user_row["id"]
                        st.session_state.user = dict(user_row)
                        nav("menu")
                    else:
                        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
            st.markdown(
                "<p style='text-align:center; color:#aaa; font-size:0.85rem; margin-bottom:0.5rem'>처음이신가요?</p>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
            if st.button("새 프로필 만들기"):
                st.session_state.creating_user = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        else:
            # ── 신규 사용자 생성 ──
            st.markdown("**새 프로필 만들기**")
            with st.form("create_user_form"):
                st.markdown("**계정 정보**")
                username_in = st.text_input("아이디 *", placeholder="영문, 숫자 조합 (4자 이상)")
                c_pw1, c_pw2 = st.columns(2)
                with c_pw1:
                    pw1 = st.text_input("비밀번호 *", type="password", placeholder="4자 이상")
                with c_pw2:
                    pw2 = st.text_input("비밀번호 확인 *", type="password", placeholder="동일하게 입력")

                st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
                st.markdown("**프로필 정보**")
                name = st.text_input("이름 *")

                c1, c2 = st.columns(2)
                with c1:
                    age = st.number_input("나이", 10, 100, 25)
                with c2:
                    gender = st.selectbox(
                        "성별",
                        ["male", "female", "other"],
                        format_func=lambda x: {"male": "남성", "female": "여성", "other": "기타"}[x],
                    )

                c3, c4 = st.columns(2)
                with c3:
                    height = st.number_input("키 (cm)", 100.0, 250.0, 170.0, 0.1)
                with c4:
                    weight = st.number_input("체중 (kg)", 30.0, 200.0, 65.0, 0.1)

                fitness_level = st.selectbox(
                    "운동 수준",
                    ["beginner", "intermediate", "advanced"],
                    format_func=lambda x: {
                        "beginner": "초보자",
                        "intermediate": "중급자",
                        "advanced": "고급자",
                    }[x],
                )
                goals = st.multiselect(
                    "목표 * (복수 선택 가능)",
                    ["체중감량", "근육증가", "체력향상", "건강유지", "재활/부상회복"],
                )
                health_notes = st.text_area(
                    "건강 특이사항 (선택)", placeholder="예: 무릎 부상 이력, 고혈압 등"
                )

                submitted = st.form_submit_button("가입하기", use_container_width=True)
                if submitted:
                    err = None
                    if not username_in.strip() or len(username_in.strip()) < 4:
                        err = "아이디는 4자 이상이어야 합니다."
                    elif api_username_exists(username_in.strip()):
                        err = f"'{username_in.strip()}' 아이디는 이미 사용 중입니다."
                    elif not pw1 or len(pw1) < 4:
                        err = "비밀번호는 4자 이상이어야 합니다."
                    elif pw1 != pw2:
                        err = "비밀번호가 일치하지 않습니다."
                    elif not name.strip():
                        err = "이름을 입력해주세요."
                    elif not goals:
                        err = "목표를 하나 이상 선택해주세요."

                    if err:
                        st.error(err)
                    else:
                        new_user = api_save_user(
                            name.strip(), age, gender, height, weight,
                            fitness_level, ", ".join(goals), health_notes,
                            username_in.strip(), pw1,
                        )
                        st.session_state.user_id = new_user["id"]
                        st.session_state.user = dict(new_user)
                        st.session_state.creating_user = False
                        nav("menu")

            st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
            if st.button("← 로그인으로 돌아가기"):
                st.session_state.creating_user = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════
def page_menu():
    user = st.session_state.user
    uid = st.session_state.user_id

    _, col, _ = st.columns([0.3, 2.4, 0.3])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)

        # ── 사용자 헤더 ──
        fitness_label = {
            "beginner": "초보자",
            "intermediate": "중급자",
            "advanced": "고급자",
        }.get(user.get("fitness_level", ""), user.get("fitness_level", ""))

        st.markdown(
            f"""
            <div style='display:flex; align-items:center; gap:1rem; margin-bottom:0.8rem;
                        background:{_C['user_card_bg']}; border-radius:16px; padding:1rem 1.2rem;
                        border:1px solid {_C['user_card_border']};
                        box-shadow:0 4px 20px {_C['shadow']};'>
                <div style='width:52px; height:52px;
                            background:{_C['user_avatar_grad']};
                            border-radius:50%; display:flex; align-items:center; justify-content:center;
                            color:#fff; font-size:1.3rem; font-weight:700; flex-shrink:0;
                            box-shadow:0 4px 12px {_C['avatar_shadow']};'>
                    {user['name'][0]}
                </div>
                <div>
                    <div style='font-size:1.2rem; font-weight:700; color:#1a1a2e; line-height:1.2'>{user['name']}</div>
                    <div style='font-size:0.82rem; color:{_C['text_sub']}; margin-top:3px; font-weight:500'>
                        {fitness_label} &nbsp;·&nbsp; {user.get('goal', '')}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not _cached_has_gym_data(uid):
            st.warning(
                "⚠  헬스장 기구 정보가 없습니다. 메뉴 4번에서 등록하면 AI가 더 정확한 루틴을 추천해드려요."
            )

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-weight:600; margin-bottom:0.8rem'>무엇을 할까요?</p>",
            unsafe_allow_html=True,
        )

        menus = [
            ("🏋️", "오늘의 운동 루틴 추천", "AI가 나에게 맞는 루틴을 설계해드려요", "recommend", "linear-gradient(135deg, #e8e4f8, #d4cef0)"),
            ("✅", "운동 완료 기록", "오늘 한 운동을 세트별로 기록해요", "log", "linear-gradient(135deg, #d4eeda, #c8e8d0)"),
            ("📊", "성장 대시보드", "나의 운동 기록과 성장 현황을 확인해요", "dashboard", "linear-gradient(135deg, #e0e8f8, #ccd8f0)"),
            ("🏢", "헬스장 기구 관리", "보유 기구를 등록·수정하면 더 정확한 추천이 가능해요", "gym", "linear-gradient(135deg, #f0e8f8, #e4d8f0)"),
        ]

        for icon, label, desc, target, grad in menus:
            left, right = st.columns([11, 1])
            with left:
                st.markdown(
                    f"""
                    <div class='card' style='margin-bottom:0.3rem; padding:1rem 1.4rem; background:{grad}; border:1px solid rgba(255,255,255,0.85);'>
                        <div style='display:flex; align-items:center; gap:1rem'>
                            <div style='font-size:1.5rem; width:42px; height:42px; display:flex;
                                        align-items:center; justify-content:center; flex-shrink:0;
                                        background:rgba(255,255,255,0.6); border-radius:12px;'>{icon}</div>
                            <div>
                                <div style='font-weight:700; font-size:0.98rem; color:#1a1a2e; line-height:1.3'>{label}</div>
                                <div style='color:#6b6b8a; font-size:0.82rem; margin-top:3px; font-weight:400'>{desc}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("→", key=f"menu_{target}"):
                    if target == "log":
                        st.session_state.log_index = 0
                    nav(target)

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
        if st.button("로그아웃"):
            for k in ["user_id", "user", "today_result"]:
                st.session_state[k] = None
            st.session_state.log_index = 0
            nav("login")
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ROUTINE RECOMMENDATION LOGIC (uses API client instead of direct DB)
# ══════════════════════════════════════════════════════════════════════════════
def _build_routine_prompt(user: dict, progression_context: str, gym_context: str, exercise_list: list = None) -> str:
    fitness_labels = {"beginner": "초보자", "intermediate": "중급자", "advanced": "고급자"}
    level = fitness_labels.get(user["fitness_level"], user["fitness_level"])
    bmi = round(user["weight_kg"] / ((user["height_cm"] / 100) ** 2), 1)
    prog_section = f"\n{progression_context}\n" if progression_context else ""
    if gym_context:
        gym_section = f"\n[헬스장 환경 - 아래 기구·시설만 사용하는 운동으로 구성해주세요]\n{gym_context}\n→ 위 목록에 없는 기구가 필요한 운동은 절대 추천하지 마세요.\n"
    else:
        gym_section = "\n[헬스장 환경]\n일반 헬스장 기준으로 바벨, 덤벨, 케이블 머신, 스미스 머신, 레그프레스, 랫풀다운, 체스트 플라이 머신, 시티드 로우, 레그 컬, 레그 익스텐션 등 모든 기구를 자유롭게 사용할 수 있습니다. 매 루틴마다 다양한 기구를 활용해 변화 있는 운동을 구성해주세요.\n"

    if exercise_list:
        ex_lines = "\n".join(f"- {e['name_en']} ({e['body_part']})" for e in exercise_list)
        exercise_section = (
            f"\n[사용 가능한 근력 운동 목록]\n{ex_lines}\n"
            f"\n※ name_en 필드: 반드시 위 목록에서 정확히 복사하세요."
            f"\n※ name 필드: 위 영문 운동명을 한국어로 번역해서 작성하세요. 절대 영어로 쓰지 마세요."
            f"\n   예) barbell bench press → 바벨 벤치프레스 / lat pulldown → 랫풀다운 / squat → 스쿼트\n"
        )
    else:
        exercise_section = ""

    return f"""당신은 전문 헬스 트레이너입니다.
아래 사용자 정보를 바탕으로 오늘의 헬스장 운동 루틴을 추천해주세요.

[사용자 정보]
- 나이: {user['age']}세 / 성별: {user['gender']}
- 키: {user['height_cm']}cm / 몸무게: {user['weight_kg']}kg / BMI: {bmi}
- 체력 수준: {level}
- 운동 목표: {user['goal']}
- 건강 주의사항: {user['health_notes'] or '없음'}
{prog_section}{gym_section}{exercise_section}
[출력 규칙]
1. 운동은 4~6개로 구성해주세요.
2. 목표가 여러 개라면 각 목표에 맞는 운동을 균형있게 섞어주세요.
3. weight_kg 필드에는 반드시 숫자만 입력하세요. 맨몸 운동이면 0.
4. category가 "유산소"인 운동은 반드시 아래 유산소 전용 규칙을 따르세요.
5. 반드시 아래 JSON 형식으로만 응답하세요.
6. name 필드는 반드시 한국어로 작성하세요. name_en을 그대로 복사하면 절대 안 됩니다.
   - name: 한국어 운동명 (예: "바벨 벤치프레스", "랫풀다운", "레그 컬")
   - name_en: 영문 운동명, 위 목록에서 정확히 복사
7. tip 필드는 반드시 초보자가 자세를 처음 배운다고 가정하고 아래 내용을 모두 포함해 4~6문장으로 작성하세요.
   - 시작 전 준비 자세 (그립/발 위치/등받이 각도 등 구체적 수치 포함)
   - 동작 수행 순서 (어디를 먼저 움직이는지 단계별로)
   - 호흡법 (언제 들이쉬고 내쉬는지)
   - 초보자가 자주 하는 실수와 교정 방법
   절대로 한 문장으로 요약하지 마세요.

[유산소 운동 전용 규칙]
- sets/reps/weight_kg 필드를 사용하지 말고, duration_min(분), speed_kmh(속도 km/h, 해당 없으면 0), incline_pct(경사도%, 해당 없으면 0)을 사용하세요.
- 해당 유산소의 소모 칼로리를 MET×체중(kg)×시간(h) 공식으로 계산하세요.
- 동일 칼로리를 소모할 수 있는 대체 유산소 운동을 cardio_alternatives 배열에 반드시 8개 이상 넣으세요.
- 아래 종목을 모두 포함하세요: 런닝머신, 등산, 수영, 자전거(실내), 자전거(야외), 천국의 계단, 줄넘기, 에어로빅, 로잉머신, 빠르게 걷기, 복싱/킥복싱, 댄스/줌바
- 각 대체 운동의 duration_min은 해당 종목 MET 값으로 동일 칼로리를 소모하는 시간을 역산한 값이어야 합니다.

{{
  "exercises": [
    {{
      "name": "바벨 벤치프레스",
      "name_en": "barbell bench press",
      "category": "가슴",
      "sets": 3,
      "reps": 12,
      "weight_kg": 40.0,
      "tip": "벤치에 누워 어깨뼈를 모아 가슴을 살짝 들어올린 뒤 바벨을 어깨너비보다 약간 넓게 잡으세요. 바를 가슴 중앙(젖꼭지 라인)으로 천천히 내리며 이때 숨을 들이쉬고, 밀어올릴 때 크게 내쉬세요. 팔꿈치가 90도 이상 벌어지지 않도록 약간 안쪽으로 유지하면 어깨 부담을 줄일 수 있습니다. 초보자가 가장 많이 하는 실수는 엉덩이를 벤치에서 띄우거나 손목을 꺾는 것인데, 엉덩이는 항상 벤치에 밀착하고 손목은 곧게 펴야 합니다."
    }},
    {{
      "name": "런닝머신",
      "name_en": "Running (Treadmill)",
      "category": "유산소",
      "duration_min": 30,
      "speed_kmh": 8.0,
      "incline_pct": 1.0,
      "tip": "자세를 바르게 유지하며 천천히 속도를 조절하세요.",
      "cardio_alternatives": [
        {{"name": "등산", "duration_min": 45, "speed_kmh": 0, "incline_pct": 0, "tip": "경사진 길 선택 시 효과적"}},
        {{"name": "수영", "duration_min": 28, "speed_kmh": 0, "incline_pct": 0, "tip": "자유형 기준"}},
        {{"name": "천국의 계단", "duration_min": 22, "speed_kmh": 0, "incline_pct": 0, "tip": "저속으로도 고강도 효과"}},
        {{"name": "줄넘기", "duration_min": 20, "speed_kmh": 0, "incline_pct": 0, "tip": "인터벌로 진행 시 효율적"}},
        {{"name": "자전거(실내)", "duration_min": 40, "speed_kmh": 20, "incline_pct": 0, "tip": "저항값 중간 이상 설정"}},
        {{"name": "자전거(야외)", "duration_min": 38, "speed_kmh": 18, "incline_pct": 0, "tip": "평지 기준"}},
        {{"name": "로잉머신", "duration_min": 25, "speed_kmh": 0, "incline_pct": 0, "tip": "등과 코어 함께 사용"}},
        {{"name": "빠르게 걷기", "duration_min": 55, "speed_kmh": 6, "incline_pct": 5, "tip": "경사 트레드밀 활용"}},
        {{"name": "복싱/킥복싱", "duration_min": 23, "speed_kmh": 0, "incline_pct": 0, "tip": "샌드백 기준"}},
        {{"name": "에어로빅", "duration_min": 35, "speed_kmh": 0, "incline_pct": 0, "tip": "고강도 에어로빅 클래스 기준"}},
        {{"name": "댄스/줌바", "duration_min": 38, "speed_kmh": 0, "incline_pct": 0, "tip": "활발하게 움직일수록 효과적"}}
      ]
    }}
  ],
  "advice": "오늘 운동 전체에 대한 맞춤 조언 2~3문장"
}}"""


def _build_progression_context_from_api(user_id: int, past_exercises: list) -> str:
    if not past_exercises:
        return ""
    lines = ["[운동 진행 분석 — 파생/강화 추천 시 반드시 반영]"]
    for name in past_exercises:
        history = api_get_exercise_history(user_id, name, limit=5)
        if not history:
            continue
        sessions = len(history)
        last = history[0]
        avg_reps = sum(h["reps_done"] for h in history) / sessions
        ready = sessions >= 2 and last["sets_done"] >= 3 and avg_reps >= 11.0
        status = "⬆ 레벨업 권장" if ready else "→ 현행 유지"
        lines.append(
            f"- {name}: {sessions}회 수행 | "
            f"최근 {last['sets_done']}세트×{last['reps_done']}회 / {last['weight_kg']}kg | {status}"
        )
    return "\n".join(lines)


def recommend_routine(user: dict, force_new: bool = False) -> dict:
    from openai import OpenAI
    if not force_new:
        existing = api_get_today_routine(user["id"])
        if existing:
            exs = json.loads(existing["exercises_json"])
            return {
                "routine_id": existing["id"],
                "exercises": exs,
                "advice": existing["ai_advice"],
            }

    past = api_get_recent_exercises(user["id"])
    progression_context = _build_progression_context_from_api(user["id"], past)
    from rag.gym_rag import retrieve_gym_context
    gym_context = retrieve_gym_context(user["id"])

    exercise_list = _cached_exercise_list()
    prompt = _build_routine_prompt(user, progression_context, gym_context, exercise_list)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    exercises = data.get("exercises", [])
    advice = data.get("advice", "")

    saved = api_save_routine(user["id"], json.dumps(exercises, ensure_ascii=False), advice)
    return {"routine_id": saved["id"], "exercises": exercises, "advice": advice}


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ROUTINE RECOMMENDATION
# ══════════════════════════════════════════════════════════════════════════════
def page_recommend():
    user = st.session_state.user

    _header("오늘의 운동 루틴", "AI가 설계한 맞춤 루틴")
    _back_btn()

    # ── 루틴 생성 / 캐시 로드 ──
    force_new = st.session_state.pop("force_new_routine", False)
    result = st.session_state.today_result
    if result is None:
        with st.spinner("AI가 루틴을 설계하고 있어요... ✨"):
            try:
                result = recommend_routine(user, force_new=force_new)
                st.session_state.today_result = result
            except Exception as e:
                st.error(f"루틴 생성 중 오류가 발생했습니다: {e}")
                return

    exercises = result.get("exercises", [])
    advice = result.get("advice", "")

    # ── AI 조언 버블 ──
    if advice:
        st.markdown(
            f"<div class='ai-bubble'>🤖 &nbsp; {advice}</div>",
            unsafe_allow_html=True,
        )

    # ── 요약 메트릭 ──
    categories = [ex.get("category", "") for ex in exercises]
    total_sets = sum(ex.get("sets", 3) for ex in exercises)

    c1, c2, c3 = st.columns(3)
    for col, num, label in [
        (c1, len(exercises), "운동 종목"),
        (c2, total_sets, "총 세트"),
        (c3, f"{len(exercises)*8}–{len(exercises)*12}분", "예상 시간"),
    ]:
        with col:
            st.markdown(
                f"""<div class='stat-box'>
                    <div class='stat-num'>{num}</div>
                    <div class='stat-lbl'>{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 근육 부위 분포 차트 + 운동 목록 ──
    col_chart, col_list = st.columns([1, 2])

    with col_chart:
        st.markdown("**근육 부위 분포**")
        cat_series = pd.Series(categories).value_counts()
        if not cat_series.empty:
            if _THEME == "health":
                colors = ["#4ecb9e","#1c1c2e","#2a9d74","#a8e8d0","#6bbfa0","#38b2f5","#b8e8d8"]
            else:
                colors = ["#7b68c8","#4a9b7f","#2d2d6b","#a88fd4","#6bbfa0","#4a3880","#c8b8e8"]
            fig_pie = go.Figure(
                go.Pie(
                    labels=cat_series.index.tolist(),
                    values=cat_series.values.tolist(),
                    marker=dict(
                        colors=colors[: len(cat_series)],
                        line=dict(color="rgba(255,255,255,0.8)", width=2),
                    ),
                    textfont=dict(color="#ffffff", size=12),
                    hole=0.45,
                )
            )
            fig_pie.update_layout(
                **_bw_layout(),
                height=240,
                legend=dict(
                    orientation="v",
                    font=dict(size=11),
                    x=1.02,
                    y=0.5,
                ),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_list:
        st.markdown("**운동 목록**")
        # 볼륨 바 차트 (세트×횟수)
        ex_names = [ex.get("name", "") for ex in exercises]
        volumes = [ex.get("sets", 3) * ex.get("reps", 12) for ex in exercises]

        fig_bar = go.Figure(
            go.Bar(
                x=volumes,
                y=ex_names,
                orientation="h",
                marker=dict(
                    color=volumes,
                    colorscale=_C["bar_cs"],
                    showscale=False,
                ),
                text=[f"{v}회" for v in volumes],
                textposition="outside",
                textfont=dict(size=10, color="#1a1a2e"),
            )
        )
        fig_bar.update_layout(
            **_bw_layout(),
            height=max(200, len(exercises) * 42),
            xaxis=dict(
                showgrid=True,
                gridcolor=_C["grid_color"],
                zeroline=False,
                title=dict(text="총 볼륨 (세트×횟수)", font=dict(size=11)),
            ),
            yaxis=dict(showgrid=False, autorange="reversed"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── 운동별 상세 카드 ──
    st.markdown("**운동 상세**")
    for i, ex in enumerate(exercises):
        is_cardio = ex.get("category") == "유산소"

        if is_cardio:
            alternatives = ex.get("cardio_alternatives", [])
            all_options = [ex] + alternatives  # 첫 번째가 AI 추천 기본 운동
            option_labels = []
            for opt in all_options:
                dur = opt.get("duration_min", "?")
                spd = opt.get("speed_kmh", 0)
                inc = opt.get("incline_pct", 0)
                detail_parts = [f"{dur}분"]
                if spd and spd > 0:
                    detail_parts.append(f"속도 {spd}km/h")
                if inc and inc > 0:
                    detail_parts.append(f"경사 {inc}%")
                option_labels.append(f"{opt.get('name', '')} — {', '.join(detail_parts)}")

            sess_key = f"cardio_choice_{i}"
            if sess_key not in st.session_state:
                st.session_state[sess_key] = 0

            st.markdown(
                f"""
                <div class='ex-card'>
                    <div style='display:flex; align-items:center; gap:6px; margin-bottom:5px'>
                        <span style='background:{_C['badge_grad']}; color:#fff; border-radius:6px;
                                     padding:2px 9px; font-size:0.75rem; font-weight:700;
                                     box-shadow:0 2px 6px {_C['badge_shadow']};'>{i+1}</span>
                        {_badge(ex.get("category", ""), "gray")}
                    </div>
                    <div style='font-size:0.8rem; color:{_C['text_sub']}; margin-bottom:6px; font-weight:500'>원하는 유산소 운동을 선택하세요</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            chosen_idx = st.selectbox(
                label=f"유산소 선택 #{i+1}",
                options=list(range(len(option_labels))),
                format_func=lambda idx, labels=option_labels: labels[idx],
                index=st.session_state[sess_key],
                key=f"radio_cardio_{i}",
                label_visibility="collapsed",
            )
            st.session_state[sess_key] = chosen_idx
            chosen = all_options[chosen_idx]
            tip = chosen.get("tip", ex.get("tip", ""))
            if tip:
                st.markdown(
                    f"<div style='color:#555; font-size:0.85rem; padding:4px 8px;'>💡 {tip}</div>",
                    unsafe_allow_html=True,
                )
        else:
            weight_str = (
                f"{ex.get('weight_kg', 0)} kg"
                if ex.get("weight_kg", 0) > 0
                else "자체중량"
            )
            name_kr = ex.get("name", "")
            name_en = ex.get("name_en", "")

            # API 호출해서 gif_url 가져오기
            gif_url = api_get_exercise_gif(name_kr, name_en)

            st.markdown(
                f"""
                <div style='display:flex; align-items:center; gap:8px; margin-bottom:10px; margin-top:20px'>
                    <span style='background:{_C['badge_grad']}; color:#fff; border-radius:6px;
                                 padding:2px 9px; font-size:0.75rem; font-weight:700;
                                 box-shadow:0 2px 6px {_C['badge_shadow']};'>{i+1}</span>
                    {_badge(ex.get("category", ""), "gray")}
                    <span style='font-size:1.1rem; font-weight:700; color:#1a1a2e; margin-left:4px'>{name_kr}</span>
                </div>
                """, unsafe_allow_html=True
            )

            col1, col2 = st.columns([1.5, 3])
            
            with col1:
                if gif_url:
                    st.image(gif_url, use_container_width=True)
                else:
                    st.info("운동 이미지를 준비 중입니다. 🥲")
            
            with col2:
                if ex.get("category") == "유산소":
                    duration = ex.get('duration_min', '-')
                    speed = ex.get('speed_kmh', 0)
                    incline = ex.get('incline_pct', 0)
                    extra = ""
                    if speed:
                        extra += f"&nbsp;&nbsp;<span style='color:#6b6b8a; font-size:15px;'>속도 <b>{speed} km/h</b></span>"
                    if incline:
                        extra += f"&nbsp;&nbsp;<span style='color:#6b6b8a; font-size:15px;'>경사 <b>{incline}%</b></span>"
                    st.markdown(f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
  <span style="font-size:22px;">🎯</span>
  <span style="font-size:13px; font-weight:700; color:{_C['goal_color']}; letter-spacing:0.05em;">목표</span>
  <span style="font-size:20px; font-weight:800; color:{_C['primary']};">{duration}분</span>
  {extra}
</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
<div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
  <span style="font-size:22px;">🎯</span>
  <span style="font-size:13px; font-weight:700; color:{_C['goal_color']}; letter-spacing:0.05em;">목표</span>
  <span style="font-size:20px; font-weight:800; color:{_C['primary']};">{ex.get('sets', 3)} Set &nbsp;×&nbsp; {ex.get('reps', 12)} Reps</span>
  <span style="font-size:15px; color:{_C['text_sub']}; font-weight:500;">({weight_str})</span>
</div>""", unsafe_allow_html=True)
                if ex.get("tip"):
                    st.markdown(f"""
<div style="
    margin-top: 16px;
    padding: 18px 22px;
    background: {_C['tip_bg']};
    border-left: 4px solid {_C['tip_border']};
    border-radius: 14px;
    display: flex; align-items: flex-start; gap: 14px;
">
    <span style="font-size:26px; line-height:1.3; flex-shrink:0;">✨</span>
    <div>
        <span style="font-size:12px; font-weight:800; color:{_C['tip_label']}; letter-spacing:0.08em; text-transform:uppercase;">AI Coach Tip</span><br>
        <span style="font-size:15px; color:{_C['primary']}; line-height:1.8; font-weight:500;">{ex.get('tip')}</span>
    </div>
</div>
""", unsafe_allow_html=True)
                
            st.divider()

    st.markdown("<br>", unsafe_allow_html=True)
    c_log, c_new = st.columns(2)
    with c_log:
        if st.button("✅ 지금 바로 기록하기"):
            st.session_state.log_index = 0
            nav("log")
    with c_new:
        st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
        if st.button("🔄 새 루틴 받기"):
            try:
                api_delete_today_routine(st.session_state.user["id"])
            except Exception:
                pass
            st.session_state.today_result = None
            st.session_state.force_new_routine = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WORKOUT LOGGING
# ══════════════════════════════════════════════════════════════════════════════
def page_log():
    user = st.session_state.user
    uid = st.session_state.user_id

    _header("운동 기록하기", "오늘의 운동을 세트별로 기록해요")
    _back_btn()

    # ── 루틴 확보 ──
    result = st.session_state.today_result
    if result is None:
        with st.spinner("오늘의 루틴을 불러오는 중..."):
            try:
                result = recommend_routine(user)
                st.session_state.today_result = result
            except Exception as e:
                st.error(f"루틴 로드 오류: {e}")
                return

    exercises = result.get("exercises", [])
    routine_id = result.get("routine_id")
    total = len(exercises)

    if total == 0:
        st.warning("오늘의 운동 목록이 비어 있습니다.")
        return

    # ── 기록된 운동 조회 ──
    logged = api_get_logged_names(routine_id) if routine_id else []
    done_count = len(logged)
    idx = st.session_state.log_index

    # ── 진행 상황 ──
    st.markdown(
        f"<p style='font-weight:600; margin-bottom:0.3rem'>{done_count} / {total} 완료</p>",
        unsafe_allow_html=True,
    )
    st.progress(done_count / total if total > 0 else 0)
    st.markdown("<br>", unsafe_allow_html=True)

    # ── 운동 칩 목록 ──
    chip_html = "<div style='display:flex; flex-wrap:wrap; gap:6px; margin-bottom:1.3rem'>"
    for i, ex in enumerate(exercises):
        is_done = ex["name"] in logged
        is_current = i == idx and not is_done
        if is_done:
            chip_html += f"<span style='background:{_C['chip_done_bg']}; color:#fff; border-radius:20px; padding:5px 14px; font-size:0.8rem; font-weight:600; box-shadow:0 2px 8px {_C['badge_shadow']};'>✓ {ex['name']}</span>"
        elif is_current:
            chip_html += f"<span style='background:rgba(255,255,255,0.95); color:{_C['chip_cur_color']}; border:2px solid {_C['chip_cur_border']}; border-radius:20px; padding:5px 14px; font-size:0.8rem; font-weight:700; box-shadow:0 2px 10px {_C['shadow2']};'>{ex['name']}</span>"
        else:
            chip_html += f"<span style='background:rgba(255,255,255,0.45); color:{_C['chip_none_color']}; border:1px solid {_C['chip_none_border']}; border-radius:20px; padding:5px 14px; font-size:0.8rem; font-weight:400;'>{ex['name']}</span>"
    chip_html += "</div>"
    st.markdown(chip_html, unsafe_allow_html=True)

    # ── 이미 기록된 운동 건너뛰기 ──
    while idx < total and exercises[idx]["name"] in logged:
        idx += 1
        st.session_state.log_index = idx

    # ── 완료 화면 ──
    if idx >= total or done_count >= total:
        if routine_id:
            api_complete_routine(routine_id)

        st.markdown(
            f"""
            <div style='text-align:center; padding:2.5rem 1rem;
                        background:{_C['complete_bg']};
                        border-radius:20px; border:1px solid {_C['complete_border']};
                        box-shadow:0 8px 32px {_C['complete_shadow']};'>
                <div style='font-size:3.5rem; margin-bottom:0.5rem'>🎉</div>
                <h2 style='margin-top:0; background:{_C['stat_grad']};
                           -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>
                    오늘의 운동 완료!</h2>
                <p style='color:{_C['text_sub']}; font-weight:500'>모든 운동을 기록했습니다. 수고하셨어요!</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if routine_id:
            try:
                logs = api_get_recent_logs(uid, limit=50)
                logs = [l for l in logs if True]  # already filtered by user
                if logs:
                    df = pd.DataFrame(logs)
                    rename = {"exercise_name": "운동", "sets_done": "세트",
                              "reps_done": "횟수", "weight_kg": "무게(kg)", "note": "메모"}
                    df = df.rename(columns=rename)
                    show_cols = [c for c in ["운동", "세트", "횟수", "무게(kg)", "메모"] if c in df.columns]
                    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
            except Exception:
                pass

        if st.button("메뉴로 돌아가기"):
            st.session_state.log_index = 0
            nav("menu")
        return

    # ── 현재 운동 기록 폼 ──
    ex = exercises[idx]
    weight_hint = (
        f"{ex.get('weight_kg', 0)} kg 권장"
        if ex.get("weight_kg", 0) > 0
        else "자체중량"
    )

    st.markdown(
        f"""
        <div class='card' style='margin-bottom:1rem; background:{_C['log_card_bg']};'>
            <div style='margin-bottom:0.6rem; display:flex; align-items:center; gap:8px;'>
                {_badge(ex.get("category", ""), "gray")}
                <span style='font-size:0.8rem; color:{_C['chip_none_color']}; font-weight:500'>{idx+1} / {total}</span>
            </div>
            <h2 style='margin:0 0 5px; font-size:1.6rem; color:#1a1a2e;'>{ex['name']}</h2>
            <p style='color:{_C['text_sub']}; margin:0 0 1rem; font-size:0.9rem; line-height:1.6'>{ex.get('tip','')}</p>
            <div style='display:flex; gap:2rem'>
                <div>
                    <span style='font-size:1.6rem; font-weight:800; background:{_C['stat_grad']};
                                 -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>{ex.get("sets", 3)}</span>
                    <span style='color:{_C['text_sub']}; font-size:0.85rem; font-weight:500'> 세트 목표</span>
                </div>
                <div>
                    <span style='font-size:1.6rem; font-weight:800; background:{_C['reps_grad']};
                                 -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;'>{ex.get("reps", 12)}</span>
                    <span style='color:{_C['text_sub']}; font-size:0.85rem; font-weight:500'> 회 목표</span>
                </div>
                <div>
                    <span style='font-size:1.2rem; font-weight:600; color:{_C['text_sub']}'>{weight_hint}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(f"log_form_{idx}"):
        c1, c2, c3 = st.columns(3)
        with c1:
            sets_done = st.number_input("실제 세트 수", 0, 20, int(ex.get("sets", 3)))
        with c2:
            reps_done = st.number_input("실제 횟수 (회)", 0, 200, int(ex.get("reps", 12)))
        with c3:
            weight_done = st.number_input(
                "사용 무게 (kg, 자체중량=0)",
                0.0,
                500.0,
                float(ex.get("weight_kg", 0)),
                0.5,
            )
        note = st.text_input("메모 (선택)", placeholder="예: 허리 주의, 폼 개선 필요")

        submitted = st.form_submit_button("기록하고 다음으로 →")
        if submitted:
            api_save_log(uid, routine_id, ex["name"], sets_done, reps_done, weight_done, note)
            st.session_state.log_index = idx + 1
            st.rerun()

    st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
    if st.button("이 운동 건너뛰기"):
        st.session_state.log_index = idx + 1
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    uid = st.session_state.user_id
    user = st.session_state.user

    _header(f"{user['name']}의 대시보드", "운동 기록과 성장 현황")
    _back_btn()

    # ── 통계 카드 ──
    stats = _cached_stats(uid)
    c1, c2, c3, c4 = st.columns(4)
    for col, num, label in [
        (c1, stats.get("completed_routines", 0), "완료한 루틴"),
        (c2, stats.get("total_logs", 0), "총 운동 기록"),
        (c3, stats.get("active_days", 0), "활동 일수"),
        (c4, f"{stats.get('streak', 0)} 🔥", "연속 운동일"),
    ]:
        with col:
            st.markdown(
                f"""<div class='stat-box'>
                    <div class='stat-num'>{num}</div>
                    <div class='stat-lbl'>{label}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 30일 활동 히트맵 ──
    st.markdown("### 30일 활동 현황")
    try:
        recent_logs = api_get_recent_logs(uid, limit=200)
        activity: dict = {}
        for row in recent_logs:
            d = str(row.get("log_date", ""))[:10]
            if d:
                activity[d] = activity.get(d, 0) + 1
    except Exception:
        activity = {}

    today = date.today()
    dates = [(today - timedelta(days=i)) for i in range(29, -1, -1)]

    heat_html = "<div style='display:flex; flex-wrap:wrap; gap:5px; margin-bottom:0.5rem'>"
    for d in dates:
        ds = str(d)
        cnt = activity.get(ds, 0)
        bg = "#2d2d6b" if cnt >= 3 else ("#7b68c8" if cnt > 0 else "rgba(123,104,200,0.12)")
        label = d.strftime("%m/%d")
        heat_html += (
            f"<div title='{label}: {cnt}회' style='width:30px; height:30px; background:{bg}; "
            f"border-radius:6px; display:flex; align-items:center; justify-content:center; "
            f"border:1px solid rgba(255,255,255,0.4);'>"
        )
        if cnt > 0:
            heat_html += f"<span style='font-size:0.62rem; color:#fff; font-weight:700'>{cnt}</span>"
        heat_html += "</div>"
    heat_html += "</div>"
    heat_html += (
        "<div style='font-size:0.75rem; color:#6b6b8a; margin-bottom:1rem; font-weight:500'>"
        "□ 미활동 &nbsp; ■ 연보라: 1–2회 &nbsp; ■ 진보라: 3회 이상</div>"
    )
    st.markdown(heat_html, unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── 운동별 성장 현황 ──
    st.markdown("### 운동별 성장 현황")
    progress_summary = api_get_progression(uid)

    if progress_summary:
        df_prog = pd.DataFrame(progress_summary)

        # 최대 중량 바 차트
        if "max_weight" in df_prog.columns:
            df_weight = df_prog[df_prog["max_weight"] > 0]
        else:
            df_weight = pd.DataFrame()

        if not df_weight.empty:
            fig_w = go.Figure(
                go.Bar(
                    x=df_weight["exercise_name"],
                    y=df_weight["max_weight"],
                    marker=dict(
                        color=df_weight["max_weight"],
                        colorscale=[[0, "#c8b8e8"], [0.5, "#7b68c8"], [1, "#2d2d6b"]],
                        showscale=False,
                    ),
                    text=df_weight["max_weight"].apply(lambda x: f"{x} kg"),
                    textposition="outside",
                    textfont=dict(size=11, color="#1a1a2e"),
                )
            )
            fig_w.update_layout(
                **_bw_layout(),
                height=300,
                yaxis=dict(
                    showgrid=True,
                    gridcolor="rgba(123,104,200,0.12)",
                    zeroline=False,
                    title=dict(text="최대 중량 (kg)", font=dict(size=11)),
                ),
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig_w, use_container_width=True)

        # 성장 현황 테이블
        rows = []
        for _, item in df_prog.iterrows():
            ex_name = item.get("exercise_name", "")
            history = api_get_exercise_history(uid, ex_name, limit=5)
            sessions = len(history)
            avg_reps = sum(h["reps_done"] for h in history) / sessions if sessions else 0
            last = history[0] if history else {}
            ready = sessions >= 2 and last.get("sets_done", 0) >= 3 and avg_reps >= 11.0
            if ready:
                next_w = round(last.get("weight_kg", 0) * 1.075, 1)
                suggestion = f"무게를 {next_w}kg으로 늘려보세요" if last.get("weight_kg", 0) > 0 else f"횟수를 {int(avg_reps)+2}회로 늘려보세요"
            else:
                suggestion = "현재 무게와 횟수를 유지하세요"
            rows.append(
                {
                    "운동": ex_name,
                    "총 세션": item.get("total_sessions", 0),
                    "최대 중량(kg)": item.get("max_weight", 0),
                    "최대 횟수": item.get("max_reps", 0),
                    "상태": "⬆️ 레벨업 권장" if ready else "→ 유지",
                    "다음 목표": suggestion,
                }
            )

        df_table = pd.DataFrame(rows)
        st.dataframe(
            df_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "운동": st.column_config.TextColumn("운동", width="medium"),
                "상태": st.column_config.TextColumn("상태", width="small"),
                "다음 목표": st.column_config.TextColumn("다음 목표", width="large"),
            },
        )
    else:
        st.markdown(
            "<div class='card-soft' style='text-align:center; padding:2rem'>"
            "<p style='color:#aaa; margin:0'>아직 기록된 운동이 없어요. 운동을 완료하고 기록해보세요!</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # ── 최근 기록 ──
    st.markdown("### 최근 운동 기록")
    logs = api_get_recent_logs(uid, limit=20)
    if logs:
        df_logs = pd.DataFrame(logs)
        col_map = {
            "log_date": "날짜",
            "exercise_name": "운동",
            "sets_done": "세트",
            "reps_done": "횟수",
            "weight_kg": "무게(kg)",
            "note": "메모",
        }
        df_logs = df_logs.rename(columns=col_map)
        if "날짜" in df_logs.columns:
            df_logs["날짜"] = pd.to_datetime(df_logs["날짜"]).dt.strftime("%m/%d")
        display_cols = [c for c in ["날짜", "운동", "세트", "횟수", "무게(kg)", "메모"] if c in df_logs.columns]
        st.dataframe(df_logs[display_cols], use_container_width=True, hide_index=True)
    else:
        st.markdown(
            "<p style='color:#aaa'>최근 기록이 없어요.</p>", unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: GYM SETUP
# ══════════════════════════════════════════════════════════════════════════════
def page_gym():
    uid = st.session_state.user_id
    if not uid:
        st.error("로그인이 필요합니다.")
        nav("login")
        return

    _header("헬스장 기구 관리", "보유 기구를 등록하면 AI가 더 정확한 루틴을 설계해드려요")
    _back_btn()

    # ── 기존 데이터로 초기화 (최초 1회) ──
    if not st.session_state.gym_initialized:
        existing = get_gym_profile_from_api(uid)
        if existing:
            st.session_state.gym_eq_list = list(existing.get("equipment", []))
            st.session_state.gym_name_edit = existing.get("gym_name", "")
            st.session_state.gym_notes_edit = existing.get("notes", "")
        else:
            st.session_state.gym_eq_list = []
            st.session_state.gym_name_edit = ""
            st.session_state.gym_notes_edit = ""
        st.session_state.gym_initialized = True

    gym_name = st.text_input(
        "헬스장 이름", value=st.session_state.gym_name_edit, key="gym_name_input"
    )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.markdown("### 등록된 기구")

    eq_list = st.session_state.gym_eq_list
    to_delete = None

    if eq_list:
        for i, eq in enumerate(eq_list):
            with st.expander(
                f"🏋️  {eq.get('name', '기구')}  ·  {eq.get('weight_range', '')}  ·  {eq.get('quantity', 1)}개",
                expanded=False,
            ):
                c1, c2 = st.columns(2)
                with c1:
                    new_name = st.text_input("기구명", eq.get("name", ""), key=f"eq_name_{i}")
                    new_qty = st.number_input("수량", 1, 50, int(eq.get("quantity", 1)), key=f"eq_qty_{i}")
                with c2:
                    new_wr = st.text_input("중량 범위", eq.get("weight_range", ""), key=f"eq_wr_{i}")
                    new_notes = st.text_input("특이사항", eq.get("notes", ""), key=f"eq_note_{i}")

                st.session_state.gym_eq_list[i] = {
                    "name": new_name,
                    "quantity": new_qty,
                    "weight_range": new_wr,
                    "notes": new_notes,
                }

                st.markdown("<div class='btn-outline'>", unsafe_allow_html=True)
                if st.button("🗑  이 기구 삭제", key=f"del_{i}"):
                    to_delete = i
                st.markdown("</div>", unsafe_allow_html=True)

        if to_delete is not None:
            st.session_state.gym_eq_list.pop(to_delete)
            st.rerun()
    else:
        st.markdown(
            "<div class='card-soft' style='text-align:center; padding:1.5rem'>"
            "<p style='color:#aaa; margin:0'>등록된 기구가 없어요. 아래에서 추가해보세요.</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── 기구 추가 ──
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("➕  기구 추가", expanded=len(eq_list) == 0):
        with st.form("add_eq_form"):
            c1, c2 = st.columns(2)
            with c1:
                new_name = st.text_input("기구명 *", placeholder="예: 바벨")
                new_qty = st.number_input("수량", 1, 50, 1)
            with c2:
                new_wr = st.text_input("중량 범위", placeholder="예: 20–100 kg")
                new_notes = st.text_input("특이사항", placeholder="예: 고정식, 올림픽봉")
            if st.form_submit_button("추가"):
                if new_name:
                    st.session_state.gym_eq_list.append(
                        {
                            "name": new_name,
                            "quantity": new_qty,
                            "weight_range": new_wr,
                            "notes": new_notes,
                        }
                    )
                    st.rerun()
                else:
                    st.error("기구명을 입력해주세요.")

    gym_notes = st.text_area(
        "헬스장 전체 메모 (선택)",
        value=st.session_state.gym_notes_edit,
        placeholder="예: 평일 06–22시, 주말 08–20시 이용 가능",
    )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if st.button("💾  저장하기"):
        gym_data = {
            "gym_name": gym_name,
            "equipment": st.session_state.gym_eq_list,
            "notes": gym_notes,
        }
        if not gym_name.strip():
            st.error("헬스장 이름을 입력해주세요.")
        elif not gym_data["equipment"]:
            st.error("기구를 하나 이상 추가해주세요.")
        else:
            try:
                save_gym_to_vector_db(uid, gym_data)
                st.session_state.today_result = None
                st.success("✅  저장 완료! 다음 루틴 추천부터 새 기구 정보가 반영됩니다.")
            except Exception as e:
                st.error(f"저장 실패: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ══════════════════════════════════════════════════════════════════════════════
_PAGES = {
    "login": page_login,
    "menu": page_menu,
    "recommend": page_recommend,
    "log": page_log,
    "dashboard": page_dashboard,
    "gym": page_gym,
}

_PAGES[st.session_state.page]()
