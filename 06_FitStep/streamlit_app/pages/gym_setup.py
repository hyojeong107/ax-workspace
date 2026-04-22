"""
헬스장 기구 등록 / 수정 페이지
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from modules.gym_setup import get_gym_profile, setup_gym as _cli_setup_gym
from rag.gym_rag import save_gym_to_vector_db, has_gym_data
from streamlit_app.components import (
    render_section_header,
    render_page_title,
    render_empty_state,
    render_divider,
    render_badge,
)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _save_gym_data(user_id: int, gym_name: str, equipment: list, overall_notes: str):
    """입력받은 데이터를 JSON + 벡터 DB에 저장합니다."""
    import json

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, f"gym_{user_id}.json")

    gym_data = {
        "user_id":   user_id,
        "gym_name":  gym_name,
        "equipment": equipment,
        "notes":     overall_notes,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(gym_data, f, ensure_ascii=False, indent=2)

    save_gym_to_vector_db(user_id, gym_data)
    return gym_data


# ── 기구 목록 렌더 ────────────────────────────────────────────────────────────

def _render_equipment_list(profile: dict):
    """등록된 기구 목록을 카드 형식으로 렌더링합니다."""
    equipment = profile.get("equipment", [])
    if not equipment:
        render_empty_state("등록된 기구가 없습니다.", "🏋️")
        return

    gym_name = profile.get("gym_name", "헬스장")
    notes    = profile.get("notes", "")

    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:1.2rem;">'
        f'<span style="font-size:1.5rem;">🏢</span>'
        f'<div>'
        f'<div style="color:#1A1A1A;font-weight:800;font-size:1.1rem;">{gym_name}</div>'
        f'{"<div style=color:#888888;font-size:0.82rem;>" + notes + "</div>" if notes else ""}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # 기구 카드 3열 그리드
    for i in range(0, len(equipment), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(equipment):
                break
            eq = equipment[idx]
            with col:
                qty_badge = (
                    f'<span style="background:#FF4500;color:#FFFFFF;'
                    f'border:2px solid #1A1A1A;border-radius:6px;'
                    f'padding:2px 8px;font-size:0.72rem;font-weight:700;'
                    f'box-shadow:2px 2px 0 #1A1A1A;">×{eq.get("quantity",1)}</span>'
                )
                weight_html = (
                    f'<div style="color:#FF4500;font-size:0.78rem;margin-top:4px;font-weight:600;">'
                    f'⚖ {eq["weight_range"]}</div>'
                    if eq.get("weight_range") else ""
                )
                notes_html = (
                    f'<div style="color:#888888;font-size:0.75rem;margin-top:2px;">'
                    f'{eq["notes"]}</div>'
                    if eq.get("notes") else ""
                )
                st.markdown(
                    f'<div class="fs-card" style="padding:14px 16px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'<span style="color:#1A1A1A;font-weight:700;font-size:0.9rem;">{eq["name"]}</span>'
                    f'{qty_badge}</div>'
                    f'{weight_html}{notes_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── 기구 등록 폼 ──────────────────────────────────────────────────────────────

def _render_gym_form(user_id: int):
    """헬스장 기구 등록 / 수정 폼."""
    existing = get_gym_profile(user_id)
    is_update = existing is not None

    with st.form("gym_form", clear_on_submit=False):
        st.markdown(
            '<div style="color:#888888;font-size:0.85rem;margin-bottom:1rem;">'
            'AI가 이 기구 목록을 기반으로 실제 헬스장 환경에 맞는 루틴을 추천합니다.</div>',
            unsafe_allow_html=True,
        )

        gym_name = st.text_input(
            "헬스장 이름",
            value=existing["gym_name"] if existing else "",
            placeholder="예: 스포애니 강남점",
        )

        render_divider()
        render_section_header("기구 목록", "최대 20개까지 입력 가능합니다")

        # 기존 기구 데이터 불러오기
        eq_data = existing["equipment"] if existing else []

        # 동적 기구 입력 (최대 20개 슬롯)
        # session_state로 기구 수 관리
        if "eq_count" not in st.session_state:
            st.session_state["eq_count"] = max(len(eq_data), 1)

        equipment = []
        for i in range(st.session_state["eq_count"]):
            prev = eq_data[i] if i < len(eq_data) else {}
            with st.container():
                st.markdown(
                    f'<div style="color:#888888;font-size:0.78rem;'
                    f'margin-bottom:4px;">기구 {i+1}</div>',
                    unsafe_allow_html=True,
                )
                c1, c2, c3, c4 = st.columns([3, 1, 2, 2])
                with c1:
                    name = st.text_input(
                        "이름", value=prev.get("name", ""),
                        placeholder="예: 바벨 스쿼트 렉",
                        key=f"eq_name_{i}", label_visibility="collapsed",
                    )
                with c2:
                    qty = st.number_input(
                        "수량", min_value=1, max_value=20,
                        value=prev.get("quantity", 1),
                        key=f"eq_qty_{i}", label_visibility="collapsed",
                    )
                with c3:
                    wr = st.text_input(
                        "무게 범위", value=prev.get("weight_range", ""),
                        placeholder="예: 5~100kg",
                        key=f"eq_wr_{i}", label_visibility="collapsed",
                    )
                with c4:
                    note = st.text_input(
                        "특이사항", value=prev.get("notes", ""),
                        placeholder="예: 혼잡 시 대기",
                        key=f"eq_note_{i}", label_visibility="collapsed",
                    )

                if name.strip():
                    eq_item = {"name": name.strip(), "quantity": qty}
                    if wr.strip():
                        eq_item["weight_range"] = wr.strip()
                    if note.strip():
                        eq_item["notes"] = note.strip()
                    equipment.append(eq_item)

                st.markdown(
                    '<div style="border-top:1px solid #E8E0D8;margin:8px 0 12px;"></div>',
                    unsafe_allow_html=True,
                )

        render_divider()
        overall_notes = st.text_input(
            "헬스장 전체 특이사항",
            value=existing.get("notes", "") if existing else "",
            placeholder="예: 오후 6~8시 혼잡, 주차 가능",
        )

        submitted = st.form_submit_button(
            "💾 저장하기",
            use_container_width=True,
        )

    # 기구 추가 버튼 (폼 외부)
    col_add, col_sub, _ = st.columns([1, 1, 5])
    with col_add:
        if st.button("+ 기구 추가", key="add_eq"):
            st.session_state["eq_count"] = min(st.session_state.get("eq_count", 1) + 1, 20)
            st.rerun()
    with col_sub:
        if st.button("− 줄이기", key="sub_eq"):
            st.session_state["eq_count"] = max(st.session_state.get("eq_count", 1) - 1, 1)
            st.rerun()

    if submitted:
        if not gym_name.strip():
            st.error("헬스장 이름을 입력해주세요.")
            return
        if not equipment:
            st.error("기구를 최소 1개 이상 입력해주세요.")
            return

        with st.spinner("저장 중..."):
            _save_gym_data(user_id, gym_name.strip(), equipment, overall_notes)

        st.success(f"'{gym_name}' 정보가 저장되었습니다! AI 루틴 추천에 반영됩니다.")
        st.cache_data.clear()
        st.rerun()


# ── 메인 렌더 함수 ────────────────────────────────────────────────────────────

def render_gym_setup(user_id: int):
    render_page_title("헬스장 설정", "🏢", "기구 정보를 등록하면 AI가 환경에 맞는 루틴을 추천합니다")

    tab_view, tab_edit = st.tabs(["🔍 현재 등록 현황", "✏️ 등록 / 수정"])

    with tab_view:
        profile = get_gym_profile(user_id)
        if profile:
            render_section_header("등록된 기구 목록")
            _render_equipment_list(profile)
        else:
            render_empty_state(
                "등록된 헬스장 정보가 없습니다.\n'등록 / 수정' 탭에서 기구를 추가해보세요.",
                "🏢"
            )

    with tab_edit:
        render_section_header(
            "기구 정보 입력",
            "기구명 / 수량 / 무게 범위 / 특이사항 순서로 입력하세요"
        )
        _render_gym_form(user_id)
