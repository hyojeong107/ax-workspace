# 헬스장 기구 RAG 모듈
# 사용자가 등록한 헬스장 기구 정보를 벡터 DB에 저장하고 검색합니다

import os
from typing import List, Optional
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ChromaDB 저장 경로 (data/ 는 .gitignore에 포함)
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
COLLECTION_NAME = "gym_equipment"

_collection = None


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _embed(texts: List[str]) -> List[List[float]]:
    """OpenAI text-embedding-3-small 으로 텍스트를 임베딩합니다."""
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def save_gym_to_vector_db(user_id: int, gym_data: dict):
    """헬스장 기구 정보를 임베딩 후 ChromaDB에 저장합니다."""
    collection = _get_collection()

    # 기존 데이터 삭제 (업데이트 시 재등록)
    try:
        existing = collection.get(where={"user_id": user_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    documents: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []

    # 문서 1: 헬스장 전체 요약
    eq_names = ", ".join(e["name"] for e in gym_data["equipment"])
    summary = (
        f"헬스장: {gym_data['gym_name']}\n"
        f"보유 기구 전체: {eq_names}"
    )
    if gym_data.get("notes"):
        summary += f"\n특이사항: {gym_data['notes']}"

    documents.append(summary)
    metadatas.append({"user_id": user_id, "doc_type": "summary"})
    ids.append(f"{user_id}_summary")

    # 문서 2~N: 기구별 개별 문서
    for i, eq in enumerate(gym_data["equipment"]):
        lines = [f"기구명: {eq['name']}"]
        if eq.get("quantity"):
            lines.append(f"수량: {eq['quantity']}개")
        if eq.get("weight_range"):
            lines.append(f"무게 범위: {eq['weight_range']}")
        if eq.get("notes"):
            lines.append(f"비고: {eq['notes']}")

        documents.append(" / ".join(lines))
        metadatas.append({"user_id": user_id, "doc_type": "equipment", "eq_name": eq["name"]})
        ids.append(f"{user_id}_eq_{i}")

    embeddings = _embed(documents)
    collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)


def retrieve_gym_context(user_id: int) -> str:
    """해당 사용자의 헬스장 기구 정보를 전부 가져와 프롬프트용 텍스트로 반환합니다."""
    try:
        collection = _get_collection()
        results = collection.get(where={"user_id": user_id})
        if not results["documents"]:
            return ""
        # summary 문서를 맨 앞으로 정렬
        paired = list(zip(results["metadatas"], results["documents"]))
        paired.sort(key=lambda x: 0 if x[0].get("doc_type") == "summary" else 1)
        return "\n".join(doc for _, doc in paired)
    except Exception:
        return ""


def has_gym_data(user_id: int) -> bool:
    """해당 사용자의 헬스장 데이터가 벡터 DB에 존재하는지 확인합니다."""
    try:
        collection = _get_collection()
        results = collection.get(where={"user_id": user_id})
        return len(results["ids"]) > 0
    except Exception:
        return False
