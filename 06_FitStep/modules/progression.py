# 점진적 향상(Progressive Overload) 분석 모듈
# 쌓인 운동 기록을 분석해서 "이제 더 어려운 걸 해도 되는지" 판단합니다
#
# 핵심 원리: 같은 운동을 2회 이상 성공적으로 완료했으면 무게/횟수를 올릴 시점

from db.database import get_connection

def get_exercise_history(user_id: int, exercise_name: str, limit: int = 5) -> list:
    """특정 운동의 최근 기록을 시간순으로 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sets_done, reps_done, weight_kg, logged_at
        FROM workout_logs
        WHERE user_id = %s AND exercise_name = %s
        ORDER BY logged_at DESC
        LIMIT %s
    """, (user_id, exercise_name, limit))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def analyze_progression(user_id: int, exercise_name: str) -> dict:
    """
    한 운동의 진행 상태를 분석해서 다음 목표를 반환합니다.

    반환 예시:
    {
      "exercise": "스쿼트",
      "sessions": 3,               # 총 기록 횟수
      "last_sets": 3,
      "last_reps": 12,
      "last_weight": 10.0,
      "avg_reps": 11.3,
      "ready_to_progress": True,   # 레벨업 권장 여부
      "suggestion": "무게를 12.5kg으로 늘려보세요"
    }
    """
    history = get_exercise_history(user_id, exercise_name)

    if not history:
        return {"exercise": exercise_name, "sessions": 0, "ready_to_progress": False}

    sessions   = len(history)
    last       = history[0]  # 가장 최근 기록
    avg_reps   = sum(h["reps_done"] for h in history) / sessions
    avg_weight = sum(h["weight_kg"] for h in history) / sessions

    # 레벨업 판단 기준
    # 1) 2회 이상 기록이 있고
    # 2) 최근 기록의 세트 수가 목표치(3세트) 이상이고
    # 3) 평균 반복 수가 목표 범위 상단(12회)을 넘으면 → 무게 증가 권장
    ready = (
        sessions >= 2
        and last["sets_done"] >= 3
        and avg_reps >= 11.0
    )

    # 다음 단계 제안 메시지 생성
    if ready:
        if last["weight_kg"] == 0:
            # 맨몸 운동 → 난이도 높은 변형 동작 또는 횟수 증가
            suggestion = f"횟수를 {int(avg_reps) + 2}회로 늘리거나 더 어려운 변형 동작으로 도전해보세요"
        else:
            # 기구 운동 → 5~10% 무게 증가 권장
            next_weight = round(last["weight_kg"] * 1.075, 1)  # 약 7.5% 증가
            suggestion = f"무게를 {next_weight}kg으로 늘려보세요 (현재 {last['weight_kg']}kg)"
    else:
        if sessions == 1:
            suggestion = "기록이 1회뿐입니다. 한 번 더 수행하면 진도를 분석할 수 있어요"
        else:
            suggestion = "현재 무게와 횟수를 유지하며 자세를 다듬어 보세요"

    return {
        "exercise":          exercise_name,
        "sessions":          sessions,
        "last_sets":         last["sets_done"],
        "last_reps":         last["reps_done"],
        "last_weight":       last["weight_kg"],
        "avg_reps":          round(avg_reps, 1),
        "avg_weight":        round(avg_weight, 1),
        "ready_to_progress": ready,
        "suggestion":        suggestion,
    }

def build_progression_context(user_id: int, past_exercises: list) -> str:
    """
    최근 운동 목록 전체의 진행 분석 결과를 AI 프롬프트용 텍스트로 변환합니다.
    recommender.py의 프롬프트 빌더에서 호출됩니다.
    """
    if not past_exercises:
        return ""

    lines = ["[운동 진행 분석 — 파생/강화 추천 시 반드시 반영]"]

    for name in past_exercises:
        data = analyze_progression(user_id, name)
        if data["sessions"] == 0:
            continue

        status = "⬆ 레벨업 권장" if data["ready_to_progress"] else "→ 현행 유지"
        lines.append(
            f"- {name}: {data['sessions']}회 수행 | "
            f"최근 {data['last_sets']}세트×{data['last_reps']}회 / {data['last_weight']}kg | "
            f"{status} | {data['suggestion']}"
        )

    return "\n".join(lines)

def get_overall_progress_summary(user_id: int) -> list:
    """
    사용자의 전체 운동 기록 요약을 반환합니다.
    나중에 대시보드/히스토리 화면에서 사용합니다.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            exercise_name,
            COUNT(*)            AS total_sessions,
            MAX(weight_kg)      AS max_weight,
            MAX(reps_done)      AS max_reps,
            MAX(logged_at)      AS last_logged
        FROM workout_logs
        WHERE user_id = %s
        GROUP BY exercise_name
        ORDER BY total_sessions DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows
