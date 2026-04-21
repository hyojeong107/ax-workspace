"""06_5. Retrieval — ChromaDB에서 헬스장 정보 조회"""

from app.indexing import _get_collection


def retrieve_context(user_id: int) -> str:
    """사용자의 헬스장 기구 정보를 전부 가져와 프롬프트용 문자열로 반환합니다."""
    try:
        collection = _get_collection()
        results = collection.get(where={"user_id": {"$eq": user_id}})
        if not results["documents"]:
            return ""
        paired = list(zip(results["metadatas"], results["documents"]))
        paired.sort(key=lambda x: 0 if x[0].get("doc_type") == "summary" else 1)
        return "\n".join(doc for _, doc in paired)
    except Exception:
        return ""


def get_gym_data(user_id: int) -> dict | None:
    """summary 문서의 metadata에서 저장된 gym_data JSON을 반환합니다."""
    import json as _json
    try:
        collection = _get_collection()
        results = collection.get(where={"$and": [{"user_id": {"$eq": user_id}}, {"doc_type": {"$eq": "summary"}}]})
        if not results["metadatas"]:
            return None
        gym_json = results["metadatas"][0].get("gym_json")
        if not gym_json:
            return None
        data = _json.loads(gym_json)
        data["user_id"] = user_id
        return data
    except Exception:
        return None


def gym_exists(user_id: int) -> bool:
    """해당 사용자의 헬스장 데이터가 벡터 DB에 존재하는지 확인합니다."""
    try:
        collection = _get_collection()
        results = collection.get(where={"user_id": {"$eq": user_id}})
        return len(results["ids"]) > 0
    except Exception:
        return False
