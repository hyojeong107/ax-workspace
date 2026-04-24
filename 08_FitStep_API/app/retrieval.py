"""06_5. Retrieval — ChromaDB에서 헬스장/공공데이터 조회 (LangChain 기반)"""

import json
from app.indexing import _get_gym_store, _get_fitness_store, _get_exercise_store


def retrieve_context(user_id: int) -> str:
    """사용자의 헬스장 기구 정보를 전부 가져와 프롬프트용 문자열로 반환합니다."""
    try:
        store = _get_gym_store()
        results = store.get(where={"user_id": {"$eq": user_id}})
        if not results["documents"]:
            return ""
        paired = list(zip(results["metadatas"], results["documents"]))
        paired.sort(key=lambda x: 0 if x[0].get("doc_type") == "summary" else 1)
        return "\n".join(doc for _, doc in paired)
    except Exception:
        return ""


def get_gym_data(user_id: int) -> dict | None:
    """summary 문서의 metadata에서 저장된 gym_data JSON을 반환합니다."""
    try:
        store = _get_gym_store()
        results = store.get(where={"$and": [{"user_id": {"$eq": user_id}}, {"doc_type": {"$eq": "summary"}}]})
        if not results["metadatas"]:
            return None
        gym_json = results["metadatas"][0].get("gym_json")
        if not gym_json:
            return None
        data = json.loads(gym_json)
        data["user_id"] = user_id
        return data
    except Exception:
        return None


def gym_exists(user_id: int) -> bool:
    """해당 사용자의 헬스장 데이터가 벡터 DB에 존재하는지 확인합니다."""
    try:
        store = _get_gym_store()
        results = store.get(where={"user_id": {"$eq": user_id}})
        return len(results["ids"]) > 0
    except Exception:
        return False


def retrieve_fitness_context(age: int, gender: str, bmi: float) -> str:
    """체력측정 컬렉션에서 유사 사례 상위 3개를 검색해 프롬프트용 문자열로 반환합니다."""
    try:
        store = _get_fitness_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age}세 {gender_str} BMI {bmi}"
        docs = store.similarity_search(query, k=3)
        if not docs:
            return ""
        lines = [f"[유사 체력측정 사례 {i+1}] {doc.page_content}" for i, doc in enumerate(docs)]
        return "\n".join(lines)
    except Exception:
        return ""


def retrieve_exercise_recommendation(age_group: str, gender: str, bmi_grade: str) -> str:
    """운동추천 컬렉션에서 메타데이터 필터로 상위 5개를 검색해 프롬프트용 문자열로 반환합니다."""
    try:
        store = _get_exercise_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age_group} {gender_str} {bmi_grade} 추천운동"
        docs = store.similarity_search(
            query,
            k=5,
            filter={"$and": [
                {"age_group": {"$eq": age_group}},
                {"gender": {"$eq": gender_str}},
                {"bmi_grade": {"$eq": bmi_grade}},
            ]},
        )
        if not docs:
            # 필터 히트 없으면 필터 없이 유사도 검색으로 폴백
            docs = store.similarity_search(query, k=5)
        if not docs:
            return ""
        lines = [f"[운동추천 {i+1}] {doc.page_content}" for i, doc in enumerate(docs)]
        return "\n".join(lines)
    except Exception:
        return ""
