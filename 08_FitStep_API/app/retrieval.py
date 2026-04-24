"""Retrieval — ChromaDB 벡터 검색 + Contextual BM25 + RRF Hybrid Search"""

import json
import os
import pickle

from app.indexing import _get_gym_store, _get_fitness_store, _get_exercise_store

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BM25_FITNESS_PATH = os.path.join(DATA_DIR, "bm25_fitness.pkl")
BM25_EXERCISE_PATH = os.path.join(DATA_DIR, "bm25_exercise.pkl")

RRF_K = 60
VECTOR_TOP_K = 10
BM25_TOP_K = 10
FINAL_TOP_K = 5


def _tokenize(text: str) -> list[str]:
    return text.split()


def _load_bm25(path: str):
    if not os.path.exists(path):
        return None, []
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["texts"]


def _rrf_fusion(vector_ids: list[str], bm25_ids: list[str]) -> list[str]:
    """Reciprocal Rank Fusion: score = sum(1 / (k + rank))"""
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(vector_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


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
    """Hybrid Search(벡터 + BM25 + RRF)로 체력측정 유사 사례 상위 5개를 반환합니다."""
    try:
        store = _get_fitness_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age}세 {gender_str} BMI {bmi}"

        # 1. 벡터 검색 (상위 10개)
        vector_docs = store.similarity_search(query, k=VECTOR_TOP_K)
        vector_ids = [str(i) for i in range(len(vector_docs))]

        # 2. BM25 검색 (상위 10개)
        bm25, texts = _load_bm25(BM25_FITNESS_PATH)
        if bm25 is not None and texts:
            tokenized_query = _tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOP_K]
            bm25_ids = [str(i) for i in top_bm25_indices]

            # 3. RRF 융합
            fused_ids = _rrf_fusion(vector_ids, bm25_ids)[:FINAL_TOP_K]

            # 벡터 결과 + BM25 결과를 인덱스로 매핑해 최종 문서 구성
            all_docs: dict[str, str] = {}
            for i, doc in enumerate(vector_docs):
                all_docs[str(i)] = doc.page_content
            for i in top_bm25_indices:
                if str(i) not in all_docs:
                    all_docs[str(i)] = texts[i]

            result_docs = [all_docs[fid] for fid in fused_ids if fid in all_docs]
        else:
            # BM25 인덱스 없으면 벡터 검색만 사용
            result_docs = [doc.page_content for doc in vector_docs[:FINAL_TOP_K]]

        if not result_docs:
            return ""
        lines = [f"[유사 체력측정 사례 {i+1}] {text}" for i, text in enumerate(result_docs)]
        return "\n".join(lines)
    except Exception:
        return ""


def retrieve_exercise_recommendation(age_group: str, gender: str, bmi_grade: str) -> str:
    """Hybrid Search(벡터 + BM25 + RRF)로 운동추천 상위 5개를 반환합니다."""
    try:
        store = _get_exercise_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age_group} {gender_str} {bmi_grade} 추천운동"

        # 1. 벡터 검색 (메타데이터 필터 우선, 없으면 폴백)
        try:
            vector_docs = store.similarity_search(
                query,
                k=VECTOR_TOP_K,
                filter={"$and": [
                    {"age_group": {"$eq": age_group}},
                    {"gender": {"$eq": gender_str}},
                    {"bmi_grade": {"$eq": bmi_grade}},
                ]},
            )
        except Exception:
            vector_docs = []

        if not vector_docs:
            vector_docs = store.similarity_search(query, k=VECTOR_TOP_K)

        vector_ids = [str(i) for i in range(len(vector_docs))]

        # 2. BM25 검색 (상위 10개)
        bm25, texts = _load_bm25(BM25_EXERCISE_PATH)
        if bm25 is not None and texts:
            tokenized_query = _tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOP_K]
            bm25_ids = [str(i) for i in top_bm25_indices]

            # 3. RRF 융합
            fused_ids = _rrf_fusion(vector_ids, bm25_ids)[:FINAL_TOP_K]

            all_docs: dict[str, str] = {}
            for i, doc in enumerate(vector_docs):
                all_docs[str(i)] = doc.page_content
            for i in top_bm25_indices:
                if str(i) not in all_docs:
                    all_docs[str(i)] = texts[i]

            result_docs = [all_docs[fid] for fid in fused_ids if fid in all_docs]
        else:
            result_docs = [doc.page_content for doc in vector_docs[:FINAL_TOP_K]]

        if not result_docs:
            return ""
        lines = [f"[운동추천 {i+1}] {text}" for i, text in enumerate(result_docs)]
        return "\n".join(lines)
    except Exception:
        return ""
