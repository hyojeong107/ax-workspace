"""LLM Judge — GPT를 사용하는 평가 항목 (Faithfulness, Coherence)"""

import json
import os
from typing import Any, Dict, List

from openai import OpenAI


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def judge_faithfulness(answer: str, context: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    답변이 제공된 컨텍스트에 근거하는지 평가합니다 (Hallucination 측정).

    Returns:
        {"score": float (0~1), "reason": str, "hallucinated_claims": list}
    """
    client = _get_client()
    prompt = f"""다음 [컨텍스트]와 [답변]을 비교하여 Faithfulness를 평가하세요.

[컨텍스트]
{context[:2000]}

[답변]
{answer[:1500]}

평가 기준:
- 답변의 각 주장이 컨텍스트에 근거하는지 확인합니다.
- 컨텍스트에 없는 정보를 만들어낸 경우 Hallucination으로 판단합니다.

JSON 형식으로 응답하세요:
{{
  "score": 0.0~1.0,
  "reason": "평가 이유 한 줄",
  "hallucinated_claims": ["근거 없는 주장1", "근거 없는 주장2"]
}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        return {"score": 0.0, "reason": f"평가 오류: {str(e)}", "hallucinated_claims": []}


def judge_multi_agent_coherence(
    specialist_outputs: Dict[str, Any],
    final_curriculum: Dict[str, Any],
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    전문가 결과물과 최종 커리큘럼 간의 일관성을 평가합니다 (멀티에이전트 전용).

    Returns:
        {"score": float, "reason": str, "conflicts": list}
    """
    client = _get_client()

    specialists_json = json.dumps(specialist_outputs, ensure_ascii=False, indent=2)[:2000]
    curriculum_json = json.dumps(final_curriculum, ensure_ascii=False, indent=2)[:1500]

    prompt = f"""멀티에이전트 시스템에서 전문가 에이전트 결과와 최종 통합 커리큘럼의 일관성을 평가하세요.

[전문가 에이전트 결과]
{specialists_json}

[최종 통합 커리큘럼]
{curriculum_json}

평가 기준:
1. 금지 운동이 포함되지 않았는가
2. 전문가 권장 운동이 적절히 반영되었는가
3. 근육 그룹 충돌이 없는가

JSON 형식으로 응답하세요:
{{
  "score": 0.0~1.0,
  "reason": "평가 이유",
  "conflicts": ["충돌 사항1", "충돌 사항2"]
}}"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"score": 0.0, "reason": f"평가 오류: {str(e)}", "conflicts": []}
