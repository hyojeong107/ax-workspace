"""Validator — 커리큘럼 코드 기반 검증 (GPT 없음)"""

from typing import Any, Dict, List


def validate_curriculum(curriculum: Dict[str, Any]) -> Dict[str, Any]:
    """
    커리큘럼의 구조/시간/근육 그룹 규칙을 순수 Python으로 검증합니다.

    Returns:
        {
            "is_valid": bool,
            "errors": List[str],      # 코드 검증 실패 항목
            "warnings": List[str],    # 경고 (오류는 아님)
            "check_summary": dict,    # 항목별 통과 여부
        }
    """
    errors: List[str] = []
    warnings: List[str] = []
    checks: Dict[str, bool] = {}

    if "error" in curriculum:
        return {
            "is_valid": False,
            "errors": ["커리큘럼 생성 실패: " + curriculum.get("error", "")],
            "warnings": [],
            "check_summary": {},
        }

    weekly_plan: List[Dict] = curriculum.get("weekly_plan", [])
    total_days: int = curriculum.get("total_days", 0)

    # ── 1. 일수 범위 ──────────────────────────────────────────────────────────
    day_count = len(weekly_plan)
    if day_count < 3:
        errors.append(f"[일수] 운동 일수 부족 — {day_count}일 (최소 3일)")
        checks["day_count_min"] = False
    elif day_count > 5:
        errors.append(f"[일수] 운동 일수 초과 — {day_count}일 (최대 5일)")
        checks["day_count_max"] = False
    else:
        checks["day_count_min"] = True
        checks["day_count_max"] = True

    # ── 2. total_days 일치 ────────────────────────────────────────────────────
    if total_days != day_count:
        warnings.append(f"[메타] total_days({total_days})와 실제 계획 일수({day_count}) 불일치")
        checks["total_days_match"] = False
    else:
        checks["total_days_match"] = True

    # ── 3. 세션별 검증 ────────────────────────────────────────────────────────
    focus_sequence: List[str] = []
    all_sessions_valid = True

    for session in weekly_plan:
        day_label = session.get("day", "?")
        duration = session.get("duration_minutes", 0)
        exercises = session.get("exercises", [])
        focus = session.get("focus", "")
        focus_sequence.append(focus)

        if duration < 40:
            errors.append(f"[{day_label}] 세션 시간 부족 — {duration}분 (최소 40분)")
            all_sessions_valid = False
        elif duration > 90:
            errors.append(f"[{day_label}] 세션 시간 초과 — {duration}분 (최대 90분)")
            all_sessions_valid = False

        if not exercises:
            errors.append(f"[{day_label}] 운동 목록 비어있음")
            all_sessions_valid = False
        else:
            # 각 운동에 필수 필드 확인
            for ex in exercises:
                if not ex.get("name"):
                    errors.append(f"[{day_label}] 운동명 누락")
                    all_sessions_valid = False
                if ex.get("sets", 0) <= 0:
                    warnings.append(f"[{day_label}] '{ex.get('name', '?')}' 세트 수 미설정")

    checks["session_duration"] = all_sessions_valid

    # ── 4. 연속 동일 근육 그룹 ────────────────────────────────────────────────
    muscle_conflict = False
    for i in range(len(focus_sequence) - 1):
        if focus_sequence[i] and focus_sequence[i] == focus_sequence[i + 1]:
            errors.append(
                f"[근육 그룹] '{focus_sequence[i]}' 연속 이틀 훈련 위반"
            )
            muscle_conflict = True
    checks["muscle_group_rule"] = not muscle_conflict

    # ── 5. summary / notes 존재 여부 ─────────────────────────────────────────
    checks["has_summary"] = bool(curriculum.get("summary"))
    if not checks["has_summary"]:
        warnings.append("[메타] summary 필드 없음")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "check_summary": checks,
    }
