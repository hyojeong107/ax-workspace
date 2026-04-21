"""06_4. Indexing — 헬스장 기구 정보를 ChromaDB에 저장"""

import os
from typing import List
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from app.schemas import GymData

load_dotenv()

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
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]


def index_gym(user_id: int, gym_data: GymData) -> int:
    """헬스장 데이터를 임베딩 후 ChromaDB에 저장합니다. 저장된 문서 수를 반환합니다."""
    collection = _get_collection()

    # 기존 데이터 삭제 (재등록 시 덮어씀)
    try:
        existing = collection.get(where={"user_id": {"$eq": user_id}})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    documents: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []

    # 문서 1: 헬스장 전체 요약
    eq_names = ", ".join(e.name for e in gym_data.equipment)
    summary = f"헬스장: {gym_data.gym_name}\n보유 기구 전체: {eq_names}"
    if gym_data.notes:
        summary += f"\n특이사항: {gym_data.notes}"

    import json as _json
    documents.append(summary)
    gym_json = _json.dumps(
        {
            "gym_name": gym_data.gym_name,
            "equipment": [e.model_dump(exclude_none=True) for e in gym_data.equipment],
            "notes": gym_data.notes or "",
        },
        ensure_ascii=False,
    )
    metadatas.append({"user_id": user_id, "doc_type": "summary", "gym_json": gym_json})
    ids.append(f"{user_id}_summary")

    # 문서 2~N: 기구별 개별 문서
    for i, eq in enumerate(gym_data.equipment):
        lines = [f"기구명: {eq.name}"]
        if eq.quantity:
            lines.append(f"수량: {eq.quantity}개")
        if eq.weight_range:
            lines.append(f"무게 범위: {eq.weight_range}")
        if eq.notes:
            lines.append(f"비고: {eq.notes}")

        documents.append(" / ".join(lines))
        metadatas.append({"user_id": user_id, "doc_type": "equipment", "eq_name": eq.name})
        ids.append(f"{user_id}_eq_{i}")

    embeddings = _embed(documents)
    collection.add(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)
    return len(documents)
