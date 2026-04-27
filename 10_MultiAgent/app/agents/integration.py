"""Integration Agent — 전문가 결과물을 하나의 커리큘럼으로 통합 (GPT 1회)"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


def _load_prompt(filename: str) -> str:
    path = Path(__file__).parent.parent.parent / "prompts" / filename
    return path.read_text(encoding="utf-8")


def run_integration_agent(
    client: OpenAI,
    user_profile: Dict[str, Any],
    strength_result: Optional[Dict[str, Any]],
    cardio_result: Optional[Dict[str, Any]],
    rehab_result: Optional[Dict[str, Any]],
    available_exercises_text: str,
    validation_errors: Optional[List[str]] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    전문가 에이전트 결과를 통합해 최종 커리큘럼 JSON을 생성합니다.
    validation_errors가 있으면 이전 시도의 오류를 수정 지시에 포함합니다.
    """
    system_prompt = _load_prompt("integration_agent.txt")

    age = user_profile.get("age", "미상")
    gender_raw = user_profile.get("gender", "M")
    gender_str = "남성" if gender_raw in ("M", "남성") else "여성"
    bmi_grade = user_profile.get("bmi_grade", "")

    parts = [f"사용자: {age}세 {gender_str}, BMI {bmi_grade}\n"]
    specialists_used = []

    if strength_result and "error" not in strength_result:
        specialists_used.append("strength")
        parts.append(f"[근력 전문가 결과]\n{json.dumps(strength_result, ensure_ascii=False, indent=2)}\n")

    if cardio_result and "error" not in cardio_result:
        specialists_used.append("cardio")
        parts.append(f"[유산소 전문가 결과]\n{json.dumps(cardio_result, ensure_ascii=False, indent=2)}\n")

    if rehab_result and "error" not in rehab_result:
        specialists_used.append("rehab")
        forbidden = rehab_result.get("forbidden_exercises", [])
        if forbidden:
            parts.append(f"[재활 가이드라인 — 금지 운동: {', '.join(forbidden)}]\n{json.dumps(rehab_result, ensure_ascii=False, indent=2)}\n")

    parts.append(available_exercises_text)

    if validation_errors:
        error_text = "\n".join(f"  - {e}" for e in validation_errors)
        parts.append(f"\n⚠️ 이전 커리큘럼 검증 실패 — 아래 오류를 반드시 수정하세요:\n{error_text}\n")

    user_content = "\n".join(parts) + "\n위 정보를 통합해 최종 주간 커리큘럼 JSON을 생성하세요."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        result = json.loads(raw)
        result["specialists_used"] = specialists_used
        return result
    except json.JSONDecodeError:
        return {"error": "통합 커리큘럼 JSON 파싱 실패", "raw": raw}
