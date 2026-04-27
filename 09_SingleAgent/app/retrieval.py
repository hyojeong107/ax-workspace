"""Retrieval — Hybrid Search (Vector + BM25 + RRF + Reranking) — 08_FitStep_API 기반"""

import os
import pickle

from flashrank import Ranker, RerankRequest
from kiwipiepy import Kiwi

from app.indexing import _get_fitness_store, _get_exercise_store

_kiwi = Kiwi()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BM25_FITNESS_PATH = os.path.join(DATA_DIR, "bm25_fitness.pkl")
BM25_EXERCISE_PATH = os.path.join(DATA_DIR, "bm25_exercise.pkl")

RRF_K = 60
VECTOR_TOP_K = 10
BM25_TOP_K = 10
RRF_TOP_K = 10
FINAL_TOP_K = 3

_reranker: Ranker | None = None


def _get_reranker() -> Ranker:
    global _reranker
    if _reranker is None:
        _reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
    return _reranker


def _rerank(query: str, docs: list[str], top_k: int) -> list[str]:
    if not docs:
        return docs
    ranker = _get_reranker()
    passages = [{"id": i, "text": text} for i, text in enumerate(docs)]
    request = RerankRequest(query=query, passages=passages)
    results = ranker.rerank(request)
    ranked = sorted(results, key=lambda r: r["score"], reverse=True)
    return [docs[r["id"]] for r in ranked[:top_k]]


def _tokenize(text: str) -> list[str]:
    tokens = _kiwi.tokenize(text)
    return [t.form for t in tokens if len(t.form) > 1]


def _load_bm25(path: str):
    if not os.path.exists(path):
        return None, []
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["bm25"], data["texts"]


def _rrf_fusion(vector_ids: list[str], bm25_ids: list[str]) -> list[str]:
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(vector_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, doc_id in enumerate(bm25_ids, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores, key=lambda d: scores[d], reverse=True)


def retrieve_fitness_context(age: int, gender: str, bmi: float) -> str:
    """체력측정 유사 사례 상위 3개를 반환합니다."""
    try:
        store = _get_fitness_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age}세 {gender_str} BMI {bmi}"

        vector_docs = store.similarity_search(query, k=VECTOR_TOP_K)
        vector_ids = [str(i) for i in range(len(vector_docs))]

        bm25, texts = _load_bm25(BM25_FITNESS_PATH)
        if bm25 is not None and texts:
            tokenized_query = _tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOP_K]
            bm25_ids = [str(i) for i in top_bm25_indices]
            fused_ids = _rrf_fusion(vector_ids, bm25_ids)[:RRF_TOP_K]

            all_docs: dict[str, str] = {}
            for i, doc in enumerate(vector_docs):
                all_docs[str(i)] = doc.page_content
            for i in top_bm25_indices:
                if str(i) not in all_docs:
                    all_docs[str(i)] = texts[i]

            candidates = [all_docs[fid] for fid in fused_ids if fid in all_docs]
        else:
            candidates = [doc.page_content for doc in vector_docs[:RRF_TOP_K]]

        result_docs = _rerank(query, candidates, FINAL_TOP_K)
        if not result_docs:
            return ""
        return "\n".join(f"[유사 체력측정 사례 {i+1}] {text}" for i, text in enumerate(result_docs))
    except Exception:
        return ""


def retrieve_exercise_recommendation(age_group: str, gender: str, bmi_grade: str) -> str:
    """운동추천 상위 3개를 반환합니다."""
    try:
        store = _get_exercise_store()
        gender_str = "남성" if gender in ("M", "남성") else "여성"
        query = f"{age_group} {gender_str} {bmi_grade} 추천운동"

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

        bm25, texts = _load_bm25(BM25_EXERCISE_PATH)
        if bm25 is not None and texts:
            tokenized_query = _tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            top_bm25_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:BM25_TOP_K]
            bm25_ids = [str(i) for i in top_bm25_indices]
            fused_ids = _rrf_fusion(vector_ids, bm25_ids)[:RRF_TOP_K]

            all_docs: dict[str, str] = {}
            for i, doc in enumerate(vector_docs):
                all_docs[str(i)] = doc.page_content
            for i in top_bm25_indices:
                if str(i) not in all_docs:
                    all_docs[str(i)] = texts[i]

            candidates = [all_docs[fid] for fid in fused_ids if fid in all_docs]
        else:
            candidates = [doc.page_content for doc in vector_docs[:RRF_TOP_K]]

        result_docs = _rerank(query, candidates, FINAL_TOP_K)
        if not result_docs:
            return ""
        return "\n".join(f"[운동추천 {i+1}] {text}" for i, text in enumerate(result_docs))
    except Exception:
        return ""
