"""
FitStep 재사용 UI 컴포넌트 라이브러리 — Light Neo-Brutalist 테마
"""

import streamlit as st


# ── 컬러 토큰 ─────────────────────────────────────────────────────────────────
# BG       : #F5F0EB  (크림)
# SURFACE  : #FFFFFF  (카드)
# ACCENT   : #FF4500  (레드-오렌지)
# ACCENT2  : #1A1A1A  (거의 검정)
# MUTED    : #888888
# BORDER   : #1A1A1A  (두꺼운 검정 테두리)

GLOBAL_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>

/* ── 전체 배경 ── */
.stApp, .stAppViewContainer, [data-testid="stAppViewContainer"],
[data-testid="stApp"], section.main {
    background-color: #F5F0EB !important;
    font-family: 'DM Sans', sans-serif !important;
}
.block-container {
    background-color: #F5F0EB !important;
    padding-top: 2.5rem !important;
    max-width: 1140px !important;
}

/* ── 사이드바 ── */
[data-testid="stSidebar"] > div:first-child {
    background-color: #1A1A1A !important;
    border-right: none !important;
}

/* 사이드바 버튼 → 네비 스타일 */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #888888 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
    text-align: left !important;
    width: 100% !important;
    transition: background 0.15s, color 0.15s !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,69,0,0.12) !important;
    color: #FF4500 !important;
    transform: none !important;
}

/* ── 메인 버튼 ── */
.main .stButton > button {
    background: #FF4500 !important;
    color: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.6rem !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
    transition: box-shadow 0.1s, transform 0.1s !important;
}
.main .stButton > button:hover {
    box-shadow: 5px 5px 0 #1A1A1A !important;
    transform: translate(-1px, -1px) !important;
    opacity: 1 !important;
}
.main .stButton > button:active {
    box-shadow: 1px 1px 0 #1A1A1A !important;
    transform: translate(2px, 2px) !important;
}

/* ── 폼 제출 버튼 ── */
.stForm .stButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: #FF4500 !important;
    color: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
    transition: box-shadow 0.1s, transform 0.1s !important;
}
.stForm .stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    box-shadow: 5px 5px 0 #1A1A1A !important;
    transform: translate(-1px, -1px) !important;
}

/* ── 인풋 ── */
.stTextInput input, .stNumberInput input, textarea {
    background-color: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
    border-radius: 8px !important;
    color: #1A1A1A !important;
    font-family: 'DM Sans', sans-serif !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
}
.stTextInput input:focus, .stNumberInput input:focus, textarea:focus {
    border-color: #FF4500 !important;
    box-shadow: 3px 3px 0 #FF4500 !important;
    outline: none !important;
}

/* ── 셀렉트박스 ── */
[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
    border-radius: 8px !important;
    color: #1A1A1A !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
}
[data-baseweb="popover"] ul {
    background-color: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
}
[data-baseweb="popover"] li:hover {
    background-color: rgba(255,69,0,0.08) !important;
}

/* ── 멀티셀렉트 태그 ── */
[data-baseweb="tag"] {
    background-color: #FF4500 !important;
    border: 1px solid #1A1A1A !important;
    border-radius: 6px !important;
}

/* ── 라벨 ── */
label, .stTextInput label, .stNumberInput label,
.stSelectbox label, .stTextArea label, .stMultiSelect label {
    color: #1A1A1A !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}

/* ── 탭 ── */
[data-baseweb="tab-list"] {
    background: #FFFFFF !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 2px !important;
    border-bottom: none !important;
    border: 2px solid #1A1A1A !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
}
[data-baseweb="tab"] {
    background: transparent !important;
    color: #888888 !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    border: none !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: #FF4500 !important;
    color: #FFFFFF !important;
}
[data-testid="stTabPanel"] {
    background: transparent !important;
    padding-top: 1.2rem !important;
}

/* ── expander ── */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 2px solid #1A1A1A !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
    box-shadow: 3px 3px 0 #1A1A1A !important;
}
[data-testid="stExpander"] summary {
    color: #1A1A1A !important;
    font-weight: 700 !important;
}

/* ── 알림 ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
    border: 2px solid #1A1A1A !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* ── 스크롤바 ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F5F0EB; }
::-webkit-scrollbar-thumb { background: #CCCCCC; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #FF4500; }

/* ── 숨기기 ── */
#MainMenu, footer { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

/* ── 카드 공통 ── */
.fs-card {
    background: #FFFFFF;
    border: 2px solid #1A1A1A;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 4px 4px 0 #1A1A1A;
    transition: box-shadow 0.1s, transform 0.1s;
    margin-bottom: 12px;
}
.fs-card:hover {
    box-shadow: 6px 6px 0 #1A1A1A;
    transform: translate(-2px, -2px);
}

/* ── 일반 텍스트 ── */
p, span, div {
    color: inherit;
}
</style>
"""


def inject_global_css():
    try:
        st.html(GLOBAL_CSS)
    except AttributeError:
        st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── KPI 카드 ──────────────────────────────────────────────────────────────────

def render_kpi_card(label: str, value: str, delta: str = "", icon: str = ""):
    if delta.startswith("+") or (delta and delta[0].isdigit()):
        delta_color, delta_arrow = "#22AA44", "▲"
    elif delta.startswith("-"):
        delta_color, delta_arrow = "#FF4500", "▼"
    else:
        delta_color, delta_arrow = "#888888", ""

    delta_html = (
        f'<div style="color:{delta_color};font-size:0.75rem;font-weight:700;margin-top:6px;">'
        f'{delta_arrow} {delta}</div>'
        if delta else "<div style='height:20px;'></div>"
    )
    icon_html = f'<div style="font-size:1.6rem;margin-bottom:8px;">{icon}</div>' if icon else ""

    st.markdown(f"""
    <div class="fs-card" style="text-align:center;padding:24px 16px;">
      {icon_html}
      <div style="color:#888888;font-size:0.68rem;font-weight:700;
                  letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px;
                  white-space:nowrap;">
        {label}
      </div>
      <div style="color:#FF4500;font-size:2.6rem;font-weight:800;line-height:1;
                  font-family:'Space Grotesk',sans-serif;">
        {value}
      </div>
      {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ── 운동 카드 ─────────────────────────────────────────────────────────────────

def render_exercise_card(
    name: str,
    sets: int,
    reps: int,
    weight_kg: float,
    category: str = "",
    tip: str = "",
    image_url: str = "",
):
    weight_display = "맨몸" if weight_kg == 0 else f"{weight_kg}kg"

    cat_html = (
        f'<span style="background:#FF4500;color:#FFFFFF;'
        f'border:1px solid #1A1A1A;border-radius:6px;'
        f'padding:3px 10px;font-size:0.68rem;font-weight:700;">{category}</span>'
        if category else ""
    )
    tip_html = (
        f'<div style="margin-top:14px;padding:10px 12px;'
        f'background:#FFF8F5;border-left:3px solid #FF4500;'
        f'border-radius:0 6px 6px 0;color:#555;font-size:0.8rem;line-height:1.5;">'
        f'💡 {tip}</div>'
        if tip else ""
    )
    img_html = (
        f'<img src="{image_url}" style="width:100%;height:110px;object-fit:cover;'
        f'border-radius:8px;margin-bottom:14px;border:2px solid #1A1A1A;" />'
        if image_url else ""
    )

    st.markdown(f"""
    <div class="fs-card">
      {img_html}
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <div style="font-size:1rem;font-weight:700;color:#1A1A1A;">{name}</div>
        {cat_html}
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">
        <div style="text-align:center;background:#F5F0EB;border:2px solid #1A1A1A;border-radius:8px;padding:12px 6px;">
          <div style="color:#888888;font-size:0.62rem;text-transform:uppercase;
                      letter-spacing:0.08em;margin-bottom:4px;font-weight:700;">세트</div>
          <div style="color:#1A1A1A;font-size:1.6rem;font-weight:800;font-family:'Space Grotesk',sans-serif;">{sets}</div>
        </div>
        <div style="text-align:center;background:#F5F0EB;border:2px solid #1A1A1A;border-radius:8px;padding:12px 6px;">
          <div style="color:#888888;font-size:0.62rem;text-transform:uppercase;
                      letter-spacing:0.08em;margin-bottom:4px;font-weight:700;">횟수</div>
          <div style="color:#1A1A1A;font-size:1.6rem;font-weight:800;font-family:'Space Grotesk',sans-serif;">{reps}</div>
        </div>
        <div style="text-align:center;background:#FFF0EB;border:2px solid #FF4500;border-radius:8px;padding:12px 6px;">
          <div style="color:#FF4500;font-size:0.62rem;text-transform:uppercase;
                      letter-spacing:0.08em;margin-bottom:4px;font-weight:700;">무게</div>
          <div style="color:#FF4500;font-size:1.2rem;font-weight:800;font-family:'Space Grotesk',sans-serif;">{weight_display}</div>
        </div>
      </div>
      {tip_html}
    </div>
    """, unsafe_allow_html=True)


# ── 진행 바 ───────────────────────────────────────────────────────────────────

def render_progress_bar(label: str, current: int, total: int, unit: str = ""):
    pct = min(round((current / total) * 100) if total > 0 else 0, 100)
    st.markdown(f"""
    <div style="margin-bottom:1.2rem;">
      <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
        <span style="color:#1A1A1A;font-size:0.88rem;font-weight:700;">{label}</span>
        <div>
          <span style="color:#888888;font-size:0.78rem;">{current}{unit} / {total}{unit}&nbsp;&nbsp;</span>
          <span style="color:#FF4500;font-size:0.82rem;font-weight:800;">{pct}%</span>
        </div>
      </div>
      <div style="background:#E8E0D8;height:10px;border-radius:5px;overflow:hidden;
                  border:1.5px solid #1A1A1A;">
        <div style="width:{pct}%;height:100%;
                    background:#FF4500;
                    border-radius:4px;"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── 배지 ─────────────────────────────────────────────────────────────────────

def render_badge(text: str, color: str = "orange"):
    pal = {
        "orange": ("#FFFFFF", "#FF4500",  "#1A1A1A"),
        "dark":   ("#FFFFFF", "#1A1A1A",  "#1A1A1A"),
        "gray":   ("#1A1A1A", "#E8E0D8",  "#1A1A1A"),
    }
    fg, bg, border = pal.get(color, pal["orange"])
    st.markdown(
        f'<span style="background:{bg};color:{fg};border:2px solid {border};'
        f'border-radius:6px;padding:4px 14px;font-size:0.75rem;font-weight:700;'
        f'box-shadow:2px 2px 0 {border};">'
        f'{text}</span>',
        unsafe_allow_html=True,
    )


# ── 섹션 헤더 ─────────────────────────────────────────────────────────────────

def render_section_header(title: str, subtitle: str = ""):
    sub = (
        f'<p style="color:#888888;font-size:0.82rem;margin:4px 0 0;font-weight:500;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="margin:2rem 0 1.2rem;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:4px;height:20px;background:#FF4500;border-radius:2px;"></div>
        <span style="color:#1A1A1A;font-size:1rem;font-weight:800;
                     letter-spacing:0.02em;font-family:'Space Grotesk',sans-serif;">{title}</span>
      </div>
      {sub}
    </div>
    """, unsafe_allow_html=True)


# ── 페이지 타이틀 ─────────────────────────────────────────────────────────────

def render_page_title(title: str, emoji: str = "", subtitle: str = ""):
    em = f'<span style="margin-right:10px;">{emoji}</span>' if emoji else ""
    sub = (
        f'<p style="color:#888888;font-size:0.9rem;margin:6px 0 0;font-weight:500;">{subtitle}</p>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="margin-bottom:2rem;padding-bottom:1.2rem;
                border-bottom:2px solid #1A1A1A;">
      <h1 style="font-size:2.2rem;font-weight:800;color:#1A1A1A;margin:0;
                 font-family:'Space Grotesk',sans-serif;letter-spacing:-0.02em;">
        {em}{title}
      </h1>
      {sub}
    </div>
    """, unsafe_allow_html=True)


# ── AI 조언 카드 ──────────────────────────────────────────────────────────────

def render_advice_card(advice: str):
    st.markdown(f"""
    <div style="background:#FFF0EB;
                border:2px solid #FF4500;border-radius:12px;
                padding:20px 24px;margin-bottom:1.2rem;
                box-shadow:4px 4px 0 #FF4500;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
        <span style="font-size:1.1rem;">🤖</span>
        <span style="color:#FF4500;font-size:0.72rem;font-weight:800;
                     letter-spacing:0.1em;text-transform:uppercase;">AI 조언</span>
      </div>
      <p style="color:#1A1A1A;font-size:0.9rem;line-height:1.75;margin:0;font-weight:500;">{advice}</p>
    </div>
    """, unsafe_allow_html=True)


# ── 구분선 ────────────────────────────────────────────────────────────────────

def render_divider():
    st.markdown(
        '<div style="height:2px;background:#E8E0D8;margin:1.5rem 0;"></div>',
        unsafe_allow_html=True,
    )


# ── 빈 상태 ──────────────────────────────────────────────────────────────────

def render_empty_state(message: str, emoji: str = "💪"):
    st.markdown(f"""
    <div style="text-align:center;padding:3rem 1rem;background:#FFFFFF;
                border:2px dashed #CCCCCC;border-radius:12px;margin:1rem 0;">
      <div style="font-size:2.8rem;margin-bottom:12px;">{emoji}</div>
      <p style="color:#888888;font-size:0.9rem;line-height:1.7;margin:0;
                white-space:pre-line;font-weight:500;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


# ── 상태 배지 ─────────────────────────────────────────────────────────────────

def render_status_badge(ready: bool):
    if ready:
        st.markdown(
            '<span style="background:#FF4500;color:#FFFFFF;'
            'border:2px solid #1A1A1A;border-radius:6px;'
            'padding:4px 12px;font-size:0.72rem;font-weight:800;'
            'box-shadow:2px 2px 0 #1A1A1A;">⬆ 레벨업!</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span style="background:#E8E0D8;color:#888888;'
            'border:2px solid #CCCCCC;border-radius:6px;'
            'padding:4px 12px;font-size:0.72rem;font-weight:600;">→ 유지</span>',
            unsafe_allow_html=True,
        )
