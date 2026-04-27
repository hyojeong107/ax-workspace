"""Tools — Agent가 호출할 도구 정의 및 실행 로직"""

import json
import os
from typing import Any, Dict, List, Optional

from app.retrieval import retrieve_fitness_context, retrieve_exercise_recommendation

# ── OpenAI tool 스펙 정의 ─────────────────────────────────────────────────────

TOOL_SPECS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_rag",
            "description": (
                "내부 RAG DB에서 사용자 프로필(나이/성별/BMI)과 운동 추천 데이터를 검색합니다. "
                "헬스장 기구 정보도 함께 포함합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "description": "사용자 나이"},
                    "gender": {"type": "string", "description": "성별 (M 또는 F)"},
                    "bmi": {"type": "number", "description": "BMI 수치"},
                    "age_group": {"type": "string", "description": "연령대 (예: 30대)"},
                    "bmi_grade": {"type": "string", "description": "BMI 등급 (저체중/정상/과체중/비만/고도비만)"},
                    "gym_info": {"type": "string", "description": "헬스장 기구 정보 텍스트 (선택)"},
                },
                "required": ["age", "gender", "bmi", "age_group", "bmi_grade"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Tavily를 통해 외부 웹에서 운동 과학 정보, 특수 건강 조건 관련 자료를 검색합니다. "
                "RAG 결과가 부족하거나 사용자가 특수 조건(부상, 질환 등)을 언급할 때 호출합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색 쿼리"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_curriculum",
            "description": (
                "수집된 컨텍스트를 기반으로 주간 운동 커리큘럼을 JSON 형식으로 생성합니다. "
                "search_rag 또는 search_web 호출 후에만 사용합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_profile": {"type": "object", "description": "사용자 프로필 (나이, 성별, BMI 등)"},
                    "rag_context": {"type": "string", "description": "RAG 검색 결과 텍스트"},
                    "web_context": {"type": "string", "description": "웹 검색 결과 텍스트 (선택)"},
                    "gym_info": {"type": "string", "description": "헬스장 기구 정보 (선택)"},
                    "special_notes": {"type": "string", "description": "특수 조건 메모 (부상, 질환 등)"},
                },
                "required": ["user_profile", "rag_context"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_curriculum",
            "description": "생성된 커리큘럼의 시간/구조/그룹 규칙을 검증합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "curriculum": {"type": "object", "description": "검증할 커리큘럼 JSON"},
                },
                "required": ["curriculum"],
            },
        },
    },
]


# ── 도구 실행 함수 ────────────────────────────────────────────────────────────

def run_search_rag(args: Dict[str, Any]) -> str:
    age = args.get("age", 30)
    gender = args.get("gender", "M")
    bmi = args.get("bmi", 22.0)
    age_group = args.get("age_group", "30대")
    bmi_grade = args.get("bmi_grade", "정상")
    gym_info = args.get("gym_info", "")

    fitness_ctx = retrieve_fitness_context(age, gender, bmi)
    exercise_ctx = retrieve_exercise_recommendation(age_group, gender, bmi_grade)

    parts = []
    if gym_info:
        parts.append(f"[헬스장 기구 정보]\n{gym_info}")
    if fitness_ctx:
        parts.append(f"[유사 체력측정 사례]\n{fitness_ctx}")
    if exercise_ctx:
        parts.append(f"[추천 운동 정보]\n{exercise_ctx}")

    return "\n\n".join(parts) if parts else "관련 데이터를 찾을 수 없습니다."


def run_search_web(args: Dict[str, Any]) -> str:
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return "TAVILY_API_KEY가 설정되지 않아 웹 검색을 수행할 수 없습니다."
        client = TavilyClient(api_key=api_key)
        query = args.get("query", "")
        response = client.search(query=query, max_results=3, search_depth="basic")
        results = response.get("results", [])
        if not results:
            return "웹 검색 결과가 없습니다."
        lines = []
        for i, r in enumerate(results):
            lines.append(f"[웹 검색 결과 {i+1}] {r.get('title', '')}\n{r.get('content', '')[:500]}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"웹 검색 오류: {str(e)}"


def run_generate_curriculum(args: Dict[str, Any], openai_client) -> Dict[str, Any]:
    """GPT를 호출해 구조화된 커리큘럼 JSON을 생성합니다."""
    user_profile = args.get("user_profile", {})
    rag_context = args.get("rag_context", "")
    web_context = args.get("web_context", "")
    gym_info = args.get("gym_info", "")
    special_notes = args.get("special_notes", "")

    age = user_profile.get("age", "미상")
    gender_raw = user_profile.get("gender", "M")
    gender_str = "남성" if gender_raw in ("M", "남성") else "여성"
    bmi = user_profile.get("bmi", "미상")
    age_group = user_profile.get("age_group", "")
    bmi_grade = user_profile.get("bmi_grade", "")
    is_high_risk = age_group in ("60대", "70대", "80대") or bmi_grade == "고도비만"

    context_block = ""
    if gym_info:
        context_block += f"\n[헬스장 기구]\n{gym_info}\n"
    if rag_context:
        context_block += f"\n[RAG 데이터]\n{rag_context}\n"
    if web_context:
        context_block += f"\n[웹 검색 참고]\n{web_context}\n"
    if special_notes:
        context_block += f"\n[특수 조건]\n{special_notes}\n"

    safety_note = ""
    if is_high_risk:
        safety_note = "⚠️ 고령 또는 고도비만 사용자입니다. 저강도 유산소 위주, 관절 부담 최소화 필수.\n"

    prompt = f"""다음 사용자 정보와 컨텍스트를 바탕으로 주간 운동 커리큘럼을 JSON으로 생성하세요.

사용자 정보:
- 나이: {age}세 ({age_group})
- 성별: {gender_str}
- BMI: {bmi} ({bmi_grade})
{safety_note}
{context_block}

출력 형식 (반드시 이 JSON 구조를 지키세요):
{{
  "summary": "커리큘럼 요약 1~2줄",
  "weekly_plan": [
    {{
      "day": "월요일",
      "focus": "근육 그룹명",
      "duration_minutes": 60,
      "exercises": [
        {{
          "name": "운동명",
          "sets": 3,
          "reps": "12",
          "rest_seconds": 60,
          "notes": "주의사항 (선택)"
        }}
      ]
    }}
  ],
  "total_days": 3,
  "notes": "전체 주의사항"
}}

규칙:
- 주 3~5일, 각 세션 40~90분
- 같은 근육 그룹 연속 이틀 금지
- 보유하지 않은 기구 운동 포함 금지
- 반드시 순수 JSON만 출력 (마크다운 코드블록 없이)
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "커리큘럼 JSON 파싱 실패", "raw": raw}


def run_validate_curriculum(args: Dict[str, Any]) -> Dict[str, Any]:
    """커리큘럼의 시간/구조/근육 그룹 규칙을 검증합니다."""
    curriculum = args.get("curriculum", {})
    errors = []
    warnings = []

    if "error" in curriculum:
        return {"is_valid": False, "errors": ["커리큘럼 생성 실패: " + curriculum.get("error", "")], "warnings": []}

    weekly_plan = curriculum.get("weekly_plan", [])
    total_days = curriculum.get("total_days", 0)

    # 일수 검증
    if len(weekly_plan) < 3:
        errors.append(f"운동 일수가 너무 적습니다. (현재 {len(weekly_plan)}일, 최소 3일)")
    if len(weekly_plan) > 5:
        errors.append(f"운동 일수가 너무 많습니다. (현재 {len(weekly_plan)}일, 최대 5일)")

    # 각 세션 검증
    focus_sequence = []
    for session in weekly_plan:
        duration = session.get("duration_minutes", 0)
        if duration < 40:
            errors.append(f"{session.get('day', '?')}: 세션 시간이 너무 짧습니다. ({duration}분, 최소 40분)")
        if duration > 90:
            errors.append(f"{session.get('day', '?')}: 세션 시간이 너무 깁니다. ({duration}분, 최대 90분)")

        exercises = session.get("exercises", [])
        if not exercises:
            errors.append(f"{session.get('day', '?')}: 운동 목록이 비어있습니다.")

        focus = session.get("focus", "")
        focus_sequence.append(focus)

    # 연속 같은 근육 그룹 검증
    for i in range(len(focus_sequence) - 1):
        if focus_sequence[i] and focus_sequence[i] == focus_sequence[i + 1]:
            errors.append(
                f"근육 그룹 규칙 위반: '{focus_sequence[i]}'이 연속 이틀 훈련됩니다."
            )

    # total_days 일치 여부
    if total_days != len(weekly_plan):
        warnings.append(f"total_days({total_days})와 실제 계획 일수({len(weekly_plan)})가 다릅니다.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def dispatch_tool(tool_name: str, tool_args: Dict[str, Any], openai_client=None) -> str:
    """도구 이름으로 실제 함수를 실행하고 결과를 문자열로 반환합니다."""
    if tool_name == "search_rag":
        return run_search_rag(tool_args)
    elif tool_name == "search_web":
        return run_search_web(tool_args)
    elif tool_name == "generate_curriculum":
        result = run_generate_curriculum(tool_args, openai_client)
        return json.dumps(result, ensure_ascii=False)
    elif tool_name == "validate_curriculum":
        result = run_validate_curriculum(tool_args)
        return json.dumps(result, ensure_ascii=False)
    else:
        return f"알 수 없는 도구: {tool_name}"
