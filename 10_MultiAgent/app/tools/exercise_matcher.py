"""Exercise Matcher — GPT 없이 기구 → 운동 매핑 (순수 Python)"""

import json
from typing import Any, Dict, List

EQUIPMENT_TO_EXERCISES: Dict[str, List[str]] = {
    "바벨":         ["바벨 스쿼트", "바벨 데드리프트", "바벨 벤치프레스", "바벨 로우", "바벨 오버헤드프레스"],
    "덤벨":         ["덤벨 컬", "덤벨 숄더프레스", "덤벨 런지", "덤벨 플라이", "덤벨 로우", "덤벨 데드리프트"],
    "트레드밀":     ["걷기", "조깅", "인터벌 달리기", "경사 걷기"],
    "풀업바":       ["풀업", "친업", "행잉 레그레이즈", "네거티브 풀업"],
    "케이블머신":   ["케이블 로우", "케이블 플라이", "케이블 트라이셉스 푸시다운", "케이블 컬"],
    "레그프레스":   ["레그프레스", "와이드 레그프레스", "내로우 레그프레스"],
    "스미스머신":   ["스미스머신 스쿼트", "스미스머신 런지", "스미스머신 벤치프레스"],
    "벤치":         ["바벨 벤치프레스", "인클라인 덤벨 벤치프레스", "덤벨 플라이"],
    "자전거":       ["정적 사이클링", "인터벌 사이클링"],
    "로잉머신":     ["로잉", "인터벌 로잉"],
    "저항밴드":     ["밴드 풀다운", "밴드 로우", "밴드 스쿼트", "밴드 컬", "밴드 사이드워크"],
    "폼롤러":       ["폼롤러 흉추 스트레칭", "폼롤러 IT밴드 마사지", "폼롤러 종아리 마사지"],
    "케틀벨":       ["케틀벨 스윙", "케틀벨 고블릿 스쿼트", "케틀벨 데드리프트"],
    "레그컬머신":   ["레그컬", "시티드 레그컬"],
    "레그익스텐션": ["레그익스텐션"],
    "딥스바":       ["딥스", "벤치 딥스", "트라이셉스 딥스"],
}

BODYWEIGHT_EXERCISES: List[str] = [
    "푸쉬업", "스쿼트", "플랭크", "런지", "버피",
    "마운틴클라이머", "크런치", "힙브릿지", "다이아몬드 푸쉬업",
]


def match_exercises(equipment: List[str]) -> Dict[str, Any]:
    """
    보유 기구 목록을 받아 수행 가능한 운동을 필터링합니다.
    기구 없음 → llm_fallback 모드 반환.
    """
    available: Dict[str, List[str]] = {"맨몸": BODYWEIGHT_EXERCISES}

    if not equipment:
        return {
            "mode": "llm_fallback",
            "message": "보유 기구 데이터가 없습니다. 맨몸 운동 위주로 생성합니다.",
            "available_exercises": available,
        }

    unrecognized: List[str] = []
    for item in equipment:
        key = item.strip()
        if key in EQUIPMENT_TO_EXERCISES:
            available[key] = EQUIPMENT_TO_EXERCISES[key]
        else:
            unrecognized.append(key)

    all_exercises = list({ex for exlist in available.values() for ex in exlist})

    return {
        "mode": "filtered",
        "available_exercises": available,
        "total_exercise_count": len(all_exercises),
        "unrecognized_equipment": unrecognized,
        "message": f"{len(available)}개 기구 기반 {len(all_exercises)}개 운동 필터링 완료.",
    }


def format_available_exercises(match_result: Dict[str, Any]) -> str:
    """match_exercises 결과를 프롬프트용 텍스트로 변환합니다."""
    available = match_result.get("available_exercises", {})
    if not available:
        return ""
    lines = ["[✅ 사용 가능 운동 목록 — 반드시 이 목록에서만 선택]"]
    for equip, exlist in available.items():
        lines.append(f"  [{equip}]: {', '.join(exlist)}")
    return "\n".join(lines)
