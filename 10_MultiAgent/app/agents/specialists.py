"""Specialists — 근력/유산소/재활 전문 에이전트 (각각 GPT 1회 호출)"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI


def _load_prompt(filename: str) -> str:
    path = Path(__file__).parent.parent.parent / "prompts" / filename
    return path.read_text(encoding="utf-8")


def _call_specialist(
    client: OpenAI,
    system_prompt: str,
    user_content: str,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """전문가 에이전트 GPT 호출 — JSON 응답 반환."""
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
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "JSON 파싱 실패", "raw": raw}


def run_strength_agent(
    client: OpenAI,
    user_profile: Dict[str, Any],
    rag_context: str,
    available_exercises_text: str,
) -> Dict[str, Any]:
    """근력 전문 에이전트 — 근력 운동 세션 JSON 반환."""
    system_prompt = _load_prompt("strength_agent.txt")

    age = user_profile.get("age", "미상")
    gender_raw = user_profile.get("gender", "M")
    gender_str = "남성" if gender_raw in ("M", "남성") else "여성"
    bmi = user_profile.get("bmi", "미상")
    bmi_grade = user_profile.get("bmi_grade", "")
    age_group = user_profile.get("age_group", "")
    goal = user_profile.get("goal", "")
    fitness_level = user_profile.get("fitness_level", "초급")
    is_high_risk = age_group in ("60대", "70대", "80대") or bmi_grade == "고도비만"

    safety = "⚠️ 고령/고도비만: 저중량 고반복, 관절 보호 필수\n" if is_high_risk else ""

    user_content = f"""사용자 정보:
- 나이: {age}세 ({age_group}), 성별: {gender_str}
- BMI: {bmi} ({bmi_grade}), 체력 수준: {fitness_level}
- 목표: {goal}
{safety}
{available_exercises_text}

[RAG 참고 데이터]
{rag_context}

위 정보를 바탕으로 근력 운동 세션 계획을 JSON으로 반환하세요.
출력 형식:
{{
  "sessions": [
    {{
      "day": "월요일",
      "focus": "가슴/삼두",
      "duration_minutes": 60,
      "exercises": [
        {{"name": "운동명", "sets": 3, "reps": "10", "rest_seconds": 90, "notes": ""}}
      ]
    }}
  ]
}}"""

    return _call_specialist(client, system_prompt, user_content)


def run_cardio_agent(
    client: OpenAI,
    user_profile: Dict[str, Any],
    rag_context: str,
    available_exercises_text: str,
) -> Dict[str, Any]:
    """유산소 전문 에이전트 — 유산소 운동 세션 JSON 반환."""
    system_prompt = _load_prompt("cardio_agent.txt")

    age = user_profile.get("age", 30)
    gender_raw = user_profile.get("gender", "M")
    gender_str = "남성" if gender_raw in ("M", "남성") else "여성"
    bmi = user_profile.get("bmi", 22.0)
    bmi_grade = user_profile.get("bmi_grade", "정상")
    age_group = user_profile.get("age_group", "30대")
    goal = user_profile.get("goal", "")
    fitness_level = user_profile.get("fitness_level", "초급")

    max_hr = 220 - (age if isinstance(age, int) else 30)
    zone2_low = int(max_hr * 0.6)
    zone2_high = int(max_hr * 0.7)

    user_content = f"""사용자 정보:
- 나이: {age}세 ({age_group}), 성별: {gender_str}
- BMI: {bmi} ({bmi_grade}), 체력 수준: {fitness_level}
- 목표: {goal}
- 최대 심박수: {max_hr}bpm, Zone 2 범위: {zone2_low}-{zone2_high}bpm

{available_exercises_text}

[RAG 참고 데이터]
{rag_context}

위 정보를 바탕으로 유산소 운동 세션 계획을 JSON으로 반환하세요.
출력 형식:
{{
  "sessions": [
    {{
      "day": "화요일",
      "focus": "유산소/심폐",
      "duration_minutes": 40,
      "heart_rate_zone": "Zone 2 ({zone2_low}-{zone2_high}bpm)",
      "exercises": [
        {{"name": "운동명", "sets": 1, "reps": "40분", "rest_seconds": 0, "notes": ""}}
      ]
    }}
  ]
}}"""

    return _call_specialist(client, system_prompt, user_content)


def run_rehab_agent(
    client: OpenAI,
    user_profile: Dict[str, Any],
    web_context: str,
) -> Dict[str, Any]:
    """재활 전문 에이전트 — 안전 가이드라인 및 금지 운동 JSON 반환."""
    system_prompt = _load_prompt("rehab_agent.txt")

    injury_tags = user_profile.get("injury_tags", "")
    health_notes = user_profile.get("health_notes", "")
    age = user_profile.get("age", "미상")
    age_group = user_profile.get("age_group", "")

    user_content = f"""사용자 정보:
- 나이: {age}세 ({age_group})
- 부상/특이사항: {injury_tags}
- 건강 메모: {health_notes}

[웹 검색 참고]
{web_context if web_context else "없음"}

위 정보를 바탕으로 재활 가이드라인을 JSON으로 반환하세요.
출력 형식:
{{
  "forbidden_exercises": ["제외할 운동1", "제외할 운동2"],
  "recommended_modifications": [
    {{"original": "원래 운동", "alternative": "대체 운동", "reason": "이유"}}
  ],
  "safety_notes": ["주의사항1", "주의사항2"]
}}"""

    return _call_specialist(client, system_prompt, user_content)
