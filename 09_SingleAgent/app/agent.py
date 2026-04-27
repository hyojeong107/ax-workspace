"""Agent — OpenAI tool-calling(ReAct) 루프"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from app.tools import TOOL_SPECS, dispatch_tool, run_validate_curriculum

MAX_ITERATIONS = 10   # 전체 도구 호출 최대 횟수
MAX_REGEN = 3         # 커리큘럼 재생성 최대 시도


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).parent.parent / "prompts" / "agent_system.txt"
    try:
        return prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "당신은 FitStep AI 에이전트입니다. 사용자의 운동 커리큘럼을 생성합니다."


def run_agent(
    user_message: str,
    user_profile: Optional[Dict[str, Any]] = None,
    gym_data: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    ReAct 에이전트 루프를 실행하고 결과를 반환합니다.

    Returns:
        {
            "reply": str,
            "complete": bool,
            "curriculum": dict | None,
            "validation_result": dict | None,
            "tool_calls_made": list[str],
        }
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system_prompt = _load_system_prompt()

    # 사용자 컨텍스트를 시스템 프롬프트에 주입
    if user_profile:
        profile_text = "\n[현재 사용자 프로필]\n" + json.dumps(user_profile, ensure_ascii=False, indent=2)
        system_prompt += profile_text
    if gym_data:
        gym_text = "\n[헬스장 기구 정보]\n" + json.dumps(gym_data, ensure_ascii=False, indent=2)
        system_prompt += gym_text

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

    # 이전 대화 이력 추가
    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_message})

    tool_calls_made: List[str] = []
    curriculum: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    regen_count = 0
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOL_SPECS,
            tool_choice="auto",
            temperature=0.3,
        )

        choice = response.choices[0]
        assistant_message = choice.message

        # 도구 호출이 없으면 최종 답변
        if not assistant_message.tool_calls:
            reply = assistant_message.content or ""
            return {
                "reply": reply,
                "complete": curriculum is not None and (validation_result is None or validation_result.get("is_valid", False)),
                "curriculum": curriculum,
                "validation_result": validation_result,
                "tool_calls_made": tool_calls_made,
            }

        # assistant 메시지 추가
        messages.append(assistant_message.model_dump(exclude_unset=True))

        # 도구 호출 처리
        for tc in assistant_message.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)
            tool_calls_made.append(tool_name)

            # generate_curriculum 재생성 제한
            if tool_name == "generate_curriculum":
                if regen_count >= MAX_REGEN:
                    tool_result = json.dumps(
                        {"error": f"최대 재생성 횟수({MAX_REGEN}회)에 도달했습니다."},
                        ensure_ascii=False,
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result,
                    })
                    continue
                regen_count += 1

            # 도구 실행
            if tool_name in ("generate_curriculum",):
                raw_result = dispatch_tool(tool_name, tool_args, client)
            else:
                raw_result = dispatch_tool(tool_name, tool_args)

            # curriculum 파싱
            if tool_name == "generate_curriculum":
                try:
                    curriculum = json.loads(raw_result)
                except Exception:
                    curriculum = None

            # validate_curriculum 결과 파싱
            if tool_name == "validate_curriculum":
                try:
                    validation_result = json.loads(raw_result)
                    # 검증 실패 시 재생성 유도 메시지를 result에 포함
                    if not validation_result.get("is_valid", True):
                        raw_result += "\n\n검증에 실패했습니다. generate_curriculum을 다시 호출하여 규칙을 수정하세요."
                except Exception:
                    validation_result = None

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": raw_result,
            })

    # 최대 반복 도달
    return {
        "reply": "최대 처리 횟수에 도달했습니다. 현재까지의 결과를 반환합니다.",
        "complete": curriculum is not None,
        "curriculum": curriculum,
        "validation_result": validation_result,
        "tool_calls_made": tool_calls_made,
    }
