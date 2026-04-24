"""Rule 기반 평가 — FitStep 응답 품질 검증

main.py 시스템 프롬프트의 [답변 규칙]이 실제 답변에 반영됐는지 검사합니다.
LLM 호출 없음 — 정규식 + 키워드 파싱.

검사 규칙:
  1. mentions_user_profile : 나이대·성별·BMI 등급 등 사용자 프로필 반영 여부
  2. mentions_exercise_name: 구체적 운동명 1개 이상 포함 여부
  3. safety_caution        : 고령(60대+) 또는 고도비만 케이스에서 안전 주의 언급 여부
                             (해당 없는 케이스는 자동 통과)
  4. personalization       : 테스트케이스 특수조건(낙상·골밀도·저체중 등) 반영 여부
                             (required_keywords 재활용, 없으면 자동 통과)
"""

from __future__ import annotations

# 1. 사용자 프로필 키워드
_PROFILE_KEYWORDS = [
    "20대", "30대", "40대", "50대", "60대", "70대",
    "여성", "남성", "여자", "남자",
    "bmi", "과체중", "비만", "정상", "저체중", "고도비만",
]

# 2. FitStep에서 실제 사용하는 구체적 운동명
_EXERCISE_NAMES = [
    "걷기", "조깅", "달리기", "수영", "자전거", "에어로빅", "줄넘기",
    "스쿼트", "데드리프트", "벤치프레스", "플랭크", "런지", "푸시업", "풀업",
    "레그프레스", "랫풀다운", "스트레칭", "요가", "필라테스",
    "버드독", "힙힌지", "케이블", "덤벨", "바벨", "밴드",
    "계단", "한 발 서기", "레그컬", "숄더프레스",
]

# 3. 안전 주의 키워드
_SAFETY_KEYWORDS = [
    "관절", "무리하지", "천천히", "조심", "주의", "상담", "의사",
    "부담", "충격", "보호", "안전", "무리없이", "점진적",
]

_HIGH_RISK_AGE_GROUPS = {"60대", "70대", "80대"}
_HIGH_RISK_BMI = {"고도비만"}


def check_rules(
    answer: str,
    age_group: str = "",
    bmi_grade: str = "",
    personalization_keywords: list[str] | None = None,
) -> dict:
    """FitStep 응답 품질 규칙을 검사합니다.

    Args:
        answer: AI가 생성한 답변 텍스트
        age_group: 테스트케이스의 연령대 (예: "60대")
        bmi_grade: 테스트케이스의 BMI 등급 (예: "고도비만")
        personalization_keywords: 케이스 특수조건 키워드 (testset required_keywords 재활용)

    Returns:
        {
            "mentions_user_profile": bool,
            "mentions_exercise_name": bool,
            "safety_caution": bool,
            "personalization": bool,
            "score": float,
            "matched_exercises": list[str],
        }
    """
    text = answer.lower()

    # 1. 프로필 반영 여부
    profile_ok = any(kw in text for kw in _PROFILE_KEYWORDS)

    # 2. 구체적 운동명 포함 여부
    matched_exercises = [ex for ex in _EXERCISE_NAMES if ex in text]
    exercise_ok = len(matched_exercises) >= 1

    # 3. 안전 주의 — 고령 또는 고도비만 케이스일 때만 검사
    is_high_risk = age_group in _HIGH_RISK_AGE_GROUPS or bmi_grade in _HIGH_RISK_BMI
    if is_high_risk:
        safety_ok = any(kw in text for kw in _SAFETY_KEYWORDS)
    else:
        safety_ok = True  # 해당 없는 케이스는 통과

    # 4. 특수조건 반영 — required_keywords 중 1개 이상 포함되면 통과
    if personalization_keywords:
        personalization_ok = any(kw.lower() in text for kw in personalization_keywords)
    else:
        personalization_ok = True

    detail = {
        "mentions_user_profile":  profile_ok,
        "mentions_exercise_name": exercise_ok,
        "safety_caution":         safety_ok,
        "personalization":        personalization_ok,
    }
    score = sum(detail.values()) / len(detail)

    return {
        **detail,
        "matched_exercises": matched_exercises,
        "score": score,
    }
