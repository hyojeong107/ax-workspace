"""Retrieval 평가 — Precision@K

검색된 컨텍스트 청크 중 ground_truth 키워드가 포함된 비율을 측정합니다.
LLM 호출 없음 — 순수 키워드 매칭.
"""

from __future__ import annotations


def precision_at_k(retrieved_chunks: list[str], relevant_keywords: list[str], k: int | None = None) -> float:
    """Precision@K: 상위 k개 청크 중 관련 키워드를 포함한 청크의 비율.

    Args:
        retrieved_chunks: 검색된 텍스트 청크 리스트 (순서대로 상위 k개까지 평가)
        relevant_keywords: ground_truth에서 추출한 관련 키워드 리스트
        k: 평가할 상위 청크 수 (None이면 전체)

    Returns:
        0.0 ~ 1.0 사이의 Precision@K 점수
    """
    if not retrieved_chunks or not relevant_keywords:
        return 0.0

    chunks = retrieved_chunks[:k] if k else retrieved_chunks
    keywords_lower = [kw.lower() for kw in relevant_keywords]

    relevant_count = 0
    for chunk in chunks:
        chunk_lower = chunk.lower()
        if any(kw in chunk_lower for kw in keywords_lower):
            relevant_count += 1

    return relevant_count / len(chunks)


def extract_keywords(text: str) -> list[str]:
    """텍스트에서 평가용 핵심 키워드를 추출합니다 (2자 이상 명사/단어)."""
    stopwords = {"의", "을", "를", "이", "가", "은", "는", "에", "와", "과", "로", "으로",
                 "그", "이", "저", "것", "수", "등", "및", "또는", "하며", "하고", "합니다",
                 "있습니다", "됩니다", "하는", "위한", "에서", "부터", "까지", "한다", "있다"}
    words = text.replace(",", " ").replace(".", " ").replace("(", " ").replace(")", " ").split()
    return [w for w in words if len(w) >= 2 and w not in stopwords]
