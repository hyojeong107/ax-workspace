"""06_4. Indexing — 헬스장 기구 정보를 ChromaDB에 저장 (LangChain 기반)"""

import os
import json
from typing import List

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.schemas import GymData

load_dotenv()

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
GYM_COLLECTION = "gym_equipment"
FITNESS_COLLECTION = "fitness_measurement"
EXERCISE_COLLECTION = "exercise_recommendation"

_gym_store: Chroma | None = None
_fitness_store: Chroma | None = None
_exercise_store: Chroma | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def _get_gym_store() -> Chroma:
    global _gym_store
    if _gym_store is None:
        _gym_store = Chroma(
            collection_name=GYM_COLLECTION,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_PATH,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _gym_store


def _get_fitness_store() -> Chroma:
    global _fitness_store
    if _fitness_store is None:
        _fitness_store = Chroma(
            collection_name=FITNESS_COLLECTION,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_PATH,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _fitness_store


def _get_exercise_store() -> Chroma:
    global _exercise_store
    if _exercise_store is None:
        _exercise_store = Chroma(
            collection_name=EXERCISE_COLLECTION,
            embedding_function=_get_embeddings(),
            persist_directory=CHROMA_PATH,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _exercise_store


def index_gym(user_id: int, gym_data: GymData) -> int:
    """헬스장 데이터를 임베딩 후 ChromaDB에 저장합니다. 저장된 문서 수를 반환합니다."""
    store = _get_gym_store()

    # 기존 데이터 삭제 (재등록 시 덮어씀)
    try:
        existing = store.get(where={"user_id": {"$eq": user_id}})
        if existing["ids"]:
            store.delete(ids=existing["ids"])
    except Exception:
        pass

    documents: List[Document] = []

    # 문서 1: 헬스장 전체 요약
    eq_names = ", ".join(e.name for e in gym_data.equipment)
    summary_text = f"헬스장: {gym_data.gym_name}\n보유 기구 전체: {eq_names}"
    if gym_data.notes:
        summary_text += f"\n특이사항: {gym_data.notes}"

    gym_json = json.dumps(
        {
            "gym_name": gym_data.gym_name,
            "equipment": [e.model_dump(exclude_none=True) for e in gym_data.equipment],
            "notes": gym_data.notes or "",
        },
        ensure_ascii=False,
    )
    documents.append(Document(
        page_content=summary_text,
        metadata={"user_id": user_id, "doc_type": "summary", "gym_json": gym_json},
    ))

    # 문서 2~N: 기구별 개별 문서
    for eq in gym_data.equipment:
        lines = [f"기구명: {eq.name}"]
        if eq.quantity:
            lines.append(f"수량: {eq.quantity}개")
        if eq.weight_range:
            lines.append(f"무게 범위: {eq.weight_range}")
        if eq.notes:
            lines.append(f"비고: {eq.notes}")

        documents.append(Document(
            page_content=" / ".join(lines),
            metadata={"user_id": user_id, "doc_type": "equipment", "eq_name": eq.name},
        ))

    ids = [f"{user_id}_summary"] + [f"{user_id}_eq_{i}" for i in range(len(gym_data.equipment))]
    store.add_documents(documents=documents, ids=ids)
    return len(documents)
