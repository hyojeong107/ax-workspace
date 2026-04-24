"""Requirement Coverage 평가 — 사용자 요구사항 반영도

테스트 케이스에 정의된 required_keywords 중 답변에 포함된 비율을 측정합니다.
LLM 호출 없음 — 순수 키워드 매칭.

required_keywords 예시:
  ["유산소", "주 3회", "걷기"] → 답변에 이 중 몇 개가 등장하는지 비율 측정
"""

from __future__ import annotations


def evaluate_requirement_coverage(answer: str, required_keywords: list[str]) -> float:
    """답변이 required_keywords를 얼마나 커버하는지 0.0 ~ 1.0으로 반환합니다."""
    if not required_keywords:
        return 1.0
    if not answer:
        return 0.0

    answer_lower = answer.lower()
    covered = sum(1 for kw in required_keywords if kw.lower() in answer_lower)
    return covered / len(required_keywords)


def get_coverage_detail(answer: str, required_keywords: list[str]) -> dict[str, bool]:
    """각 키워드별 커버 여부를 반환합니다 (리포트용)."""
    answer_lower = answer.lower()
    return {kw: kw.lower() in answer_lower for kw in required_keywords}
