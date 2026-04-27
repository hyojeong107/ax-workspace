"""Orchestrator — 멀티에이전트 파이프라인 메인 컨트롤러"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.agents.specialists import run_strength_agent, run_cardio_agent, run_rehab_agent
from app.agents.integration import run_integration_agent
from app.tools.exercise_matcher import match_exercises, format_available_exercises
from app.tools.rag_search import search_rag
from app.tools.web_search import search_web
from app.tools.validator import validate_curriculum

MAX_REGEN = 2  # 커리큘럼 재생성 최대 시도 (검증 실패 시)


def _load_prompt(filename: str) -> str:
    path = Path(__file__).parent.parent.parent / "prompts" / filename
    return path.read_text(encoding="utf-8")


def _analyze_specialists_needed(
    client: OpenAI,
    user_message: str,
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    오케스트레이터 GPT 호출 — 어떤 전문가가 필요한지 결정합니다.
    Returns: {"strength": bool, "cardio": bool, "rehab": bool, "reason": str}
    """
    system_prompt = _load_prompt("orchestrator.txt")

    goal = user_profile.get("goal", "")
    injury_tags = user_profile.get("injury_tags", "")
    health_notes = user_profile.get("health_notes", "")
    age_group = user_profile.get("age_group", "")
    bmi_grade = user_profile.get("bmi_grade", "")

    user_content = f"""사용자 요청: {user_message}

프로필:
- 목표: {goal}
- 연령대: {age_group}, BMI 등급: {bmi_grade}
- 부상/특이사항: {injury_tags}
- 건강 메모: {health_notes}

어떤 전문가 에이전트가 필요한지 JSON으로 응답하세요.
출력 형식:
{{"strength": true/false, "cardio": true/false, "rehab": true/false, "reason": "선택 이유"}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
        # 최소 1개 전문가는 활성화
        if not result.get("strength") and not result.get("cardio"):
            result["strength"] = True
            result["cardio"] = True
        return result
    except Exception:
        return {"strength": True, "cardio": True, "rehab": False, "reason": "기본값 (분석 실패)"}


def run_orchestrator(
    user_message: str,
    user_profile: Optional[Dict[str, Any]] = None,
    gym_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    멀티에이전트 파이프라인을 실행합니다.

    흐름:
      1. 기구 매칭 (Python, GPT 없음)
      2. RAG 검색 (Python + ChromaDB)
      3. 웹 검색 (재활 조건 있을 때만)
      4. 전문가 결정 (GPT 1회)
      5. 전문가 에이전트 호출 (각 GPT 1회)
      6. 통합 에이전트 (GPT 1회)
      7. 코드 기반 검증 (Python, GPT 없음)
      8. 검증 실패 시 재통합 (최대 MAX_REGEN회)

    Returns:
        {
            "curriculum": dict,
            "validation_result": dict,
            "matched_exercises": dict,
            "specialists_called": dict,
            "pipeline_log": list[str],   # 각 단계 처리 내역 (UI 표시용)
            "error": str | None,
        }
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_profile = user_profile or {}
    pipeline_log: List[str] = []

    # ── Step 1: 기구 매칭 (GPT 없음) ─────────────────────────────────────────
    equipment = (gym_data or {}).get("equipment", [])
    match_result = match_exercises(equipment)
    available_text = format_available_exercises(match_result)
    pipeline_log.append(
        f"[기구 매칭] {match_result['message']} (모드: {match_result['mode']})"
    )

    # ── Step 2: RAG 검색 ──────────────────────────────────────────────────────
    age = user_profile.get("age", 30)
    gender = user_profile.get("gender", "M")
    bmi = user_profile.get("bmi", 22.0)
    age_group = user_profile.get("age_group", "30대")
    bmi_grade = user_profile.get("bmi_grade", "정상")

    rag_ctx = search_rag(
        age=age, gender=gender, bmi=bmi,
        age_group=age_group, bmi_grade=bmi_grade,
    )
    pipeline_log.append("[RAG 검색] 체력측정 사례 및 운동 추천 데이터 로드 완료")

    # ── Step 3: 웹 검색 (부상/질환 있을 때만) ───────────────────────────────
    web_ctx = ""
    injury_tags = user_profile.get("injury_tags", "")
    health_notes = user_profile.get("health_notes", "")
    if injury_tags or health_notes:
        query = f"{injury_tags} {health_notes} 운동 재활 주의사항".strip()
        web_ctx = search_web(query)
        pipeline_log.append(f"[웹 검색] 특수 조건 감지 → '{query}' 검색 완료")

    # ── Step 4: 전문가 결정 (GPT 1회) ────────────────────────────────────────
    specialists = _analyze_specialists_needed(client, user_message, user_profile)
    pipeline_log.append(
        f"[전문가 결정] 근력={specialists['strength']}, "
        f"유산소={specialists['cardio']}, 재활={specialists['rehab']} "
        f"— {specialists.get('reason', '')}"
    )

    # ── Step 5: 전문가 에이전트 호출 ─────────────────────────────────────────
    strength_result = None
    cardio_result = None
    rehab_result = None

    if specialists.get("strength"):
        strength_result = run_strength_agent(client, user_profile, rag_ctx, available_text)
        status = "완료" if "error" not in strength_result else f"오류: {strength_result.get('error')}"
        pipeline_log.append(f"[근력 에이전트] {status}")

    if specialists.get("cardio"):
        cardio_result = run_cardio_agent(client, user_profile, rag_ctx, available_text)
        status = "완료" if "error" not in cardio_result else f"오류: {cardio_result.get('error')}"
        pipeline_log.append(f"[유산소 에이전트] {status}")

    if specialists.get("rehab"):
        rehab_result = run_rehab_agent(client, user_profile, web_ctx)
        forbidden = rehab_result.get("forbidden_exercises", [])
        status = f"완료 (금지 운동 {len(forbidden)}개)" if "error" not in rehab_result else "오류"
        pipeline_log.append(f"[재활 에이전트] {status}")

    # ── Step 6-8: 통합 + 검증 (최대 MAX_REGEN+1회) ───────────────────────────
    curriculum: Optional[Dict[str, Any]] = None
    validation_result: Dict[str, Any] = {}
    validation_errors: Optional[List[str]] = None

    for attempt in range(MAX_REGEN + 1):
        curriculum = run_integration_agent(
            client=client,
            user_profile=user_profile,
            strength_result=strength_result,
            cardio_result=cardio_result,
            rehab_result=rehab_result,
            available_exercises_text=available_text,
            validation_errors=validation_errors,
        )

        if "error" in curriculum:
            pipeline_log.append(f"[통합 에이전트] 시도 {attempt+1} — 오류: {curriculum.get('error')}")
            break

        validation_result = validate_curriculum(curriculum)
        pipeline_log.append(
            f"[검증] 시도 {attempt+1} — "
            f"{'✅ 통과' if validation_result['is_valid'] else f'❌ 실패 ({len(validation_result[\"errors\"])}건)'}"
        )

        if validation_result["is_valid"]:
            break

        validation_errors = validation_result["errors"]
        if attempt < MAX_REGEN:
            pipeline_log.append(f"[재생성] 검증 실패 → 오류 수정 후 재통합 시도 ({attempt+2}/{MAX_REGEN+1})")

    return {
        "curriculum": curriculum,
        "validation_result": validation_result,
        "matched_exercises": match_result,
        "specialists_called": specialists,
        "pipeline_log": pipeline_log,
        "error": curriculum.get("error") if curriculum and "error" in curriculum else None,
    }
