"""RAG Search — ChromaDB 기반 운동 데이터 검색"""

from typing import Any, Dict


def search_rag(
    age: int,
    gender: str,
    bmi: float,
    age_group: str,
    bmi_grade: str,
    gym_info: str = "",
) -> str:
    """체력측정 사례 및 운동 추천 데이터를 검색합니다."""
    try:
        from app.retrieval import retrieve_fitness_context, retrieve_exercise_recommendation

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
    except Exception as e:
        return f"RAG 검색 오류: {str(e)}"
