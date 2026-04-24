"""Faithfulness 평가 — 생성된 답변이 검색 컨텍스트에 근거하는지 측정

gpt-4o-mini를 Judge로 사용해 0.0 ~ 1.0 점수를 반환합니다.
컨텍스트가 없으면 0.0, 답변이 없으면 0.0.
"""

from __future__ import annotations

import os
from openai import OpenAI

_JUDGE_PROMPT = """\
다음 [컨텍스트]와 [답변]을 보고, 답변의 각 주장이 컨텍스트에 근거하는지 평가하세요.

[컨텍스트]
{context}

[답변]
{answer}

평가 기준:
- 컨텍스트에 명시된 정보에 기반한 주장: 근거 있음
- 컨텍스트에 없는 내용을 추가하거나 왜곡한 주장: 근거 없음 (hallucination)

답변에서 주요 주장(claim)을 파악하고, 각 주장이 컨텍스트에 근거하는지 판단하세요.
마지막 줄에 반드시 다음 형식으로만 점수를 출력하세요:
SCORE: 0.XX

(0.00 = 전혀 근거 없음, 1.00 = 모든 주장이 컨텍스트에 근거함)
"""


def evaluate_faithfulness(answer: str, contexts: list[str], client: OpenAI | None = None) -> float:
    """LLM Judge를 통해 답변의 Faithfulness 점수를 반환합니다."""
    if not answer or not contexts:
        return 0.0

    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    context_text = "\n".join(f"[{i+1}] {c}" for i, c in enumerate(contexts))
    prompt = _JUDGE_PROMPT.format(context=context_text, answer=answer)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        result_text = response.choices[0].message.content.strip()
        for line in reversed(result_text.splitlines()):
            if line.startswith("SCORE:"):
                return float(line.split(":")[1].strip())
    except Exception:
        pass
    return 0.0
