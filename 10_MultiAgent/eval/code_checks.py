"""Code Checks — GPT 없이 규칙 기반으로 평가하는 항목들"""

import re
from typing import Any, Dict, List


def check_session_count(answer: str, rules: Dict) -> bool:
    """주당 운동 횟수 언급 여부."""
    if not rules.get("expect_session_count", True):
        return True
    patterns = [r"주\s*[3-7]\s*[회일]", r"[3-7]\s*일\s*운동", r"매일", r"격일"]
    return any(re.search(p, answer) for p in patterns)


def check_duration(answer: str, rules: Dict) -> bool:
    """운동 시간 언급 여부."""
    if not rules.get("expect_duration", True):
        return True
    patterns = [r"\d+\s*분", r"\d+\s*시간", r"hour", r"minute"]
    return any(re.search(p, answer, re.IGNORECASE) for p in patterns)


def check_group_variety(answer: str, rules: Dict) -> bool:
    """근육 그룹 또는 운동 타입 다양성."""
    if not rules.get("expect_group_variety", True):
        return True
    groups = ["유산소", "근력", "스트레칭", "코어", "상체", "하체", "전신", "cardio", "strength"]
    found = sum(1 for g in groups if g in answer)
    return found >= 2


def check_intensity(answer: str, rules: Dict) -> bool:
    """운동 강도 언급 여부."""
    if not rules.get("expect_intensity", True):
        return True
    keywords = ["저강도", "중강도", "고강도", "중등도", "가볍게", "세게", "강도", "강하게", "zone"]
    return any(k in answer.lower() for k in keywords)


def check_precision_at_k(retrieved_docs: List[str], relevant_keywords: List[str], k: int = 3) -> float:
    """상위 K개 검색 문서 중 관련 키워드를 포함하는 비율."""
    if not retrieved_docs or not relevant_keywords:
        return 0.0
    top_k = retrieved_docs[:k]
    hits = sum(
        1 for doc in top_k
        if any(kw.lower() in doc.lower() for kw in relevant_keywords)
    )
    return hits / len(top_k)


def check_requirement_coverage(answer: str, required_keywords: List[str]) -> float:
    """필수 키워드가 답변에 포함된 비율."""
    if not required_keywords:
        return 1.0
    hits = sum(1 for kw in required_keywords if kw.lower() in answer.lower())
    return hits / len(required_keywords)


def run_code_checks(
    answer: str,
    retrieved_docs: List[str],
    relevant_keywords: List[str],
    required_keywords: List[str],
    rules: Dict,
    k: int = 3,
) -> Dict[str, Any]:
    """
    모든 코드 기반 검증 항목을 실행합니다.

    Returns:
        {
            "session_count": bool,
            "duration": bool,
            "group_variety": bool,
            "intensity": bool,
            "precision_at_k": float,
            "requirement_coverage": float,
            "rule_pass_rate": float,   # 규칙 항목 통과율
        }
    """
    session_ok = check_session_count(answer, rules)
    duration_ok = check_duration(answer, rules)
    variety_ok = check_group_variety(answer, rules)
    intensity_ok = check_intensity(answer, rules)

    rule_checks = [session_ok, duration_ok, variety_ok, intensity_ok]
    rule_pass_rate = sum(rule_checks) / len(rule_checks)

    return {
        "session_count": session_ok,
        "duration": duration_ok,
        "group_variety": variety_ok,
        "intensity": intensity_ok,
        "precision_at_k": check_precision_at_k(retrieved_docs, relevant_keywords, k),
        "requirement_coverage": check_requirement_coverage(answer, required_keywords),
        "rule_pass_rate": rule_pass_rate,
    }
