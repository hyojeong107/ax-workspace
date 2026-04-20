# 헬스장 기구 RAG 모듈
# 사용자가 등록한 헬스장 기구 정보를 벡터 DB에 저장하고 검색합니다
# RAG_API_URL 환경변수가 설정된 경우 08_Advanced_RAG HTTP API를 사용합니다

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# ── API 모드 헬퍼 ────────────────────────────────────────────────────────────

def _use_api() -> bool:
    return bool(os.getenv("RAG_API_URL"))

def _api_url(path: str) -> str:
    return os.getenv("RAG_API_URL", "").rstrip("/") + path

def _api_headers() -> dict:
    key = os.getenv("RAG_API_KEY", "")
    return {"X-API-Key": key} if key else {}


# ── ChromaDB 모드 (로컬 개발용) ──────────────────────────────────────────────

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
COLLECTION_NAME = "gym_equipment"
_collection = None

def _get_collection():
    import chromadb
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

def _embed(texts: List[str]) -> List[List[float]]:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]

def _chroma_save(user_id: int, gym_data: dict):
    collection = _get_collection()
    try:
        existing = collection.get(where={"user_id": user_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    documents: List[str] = []
    metadatas: List[dict] = []
    ids: List[str] = []

    eq_names = ", ".join(e["name"] for e in gym_data["equipment"])
    summary = f"헬스장: {gym_data['gym_name']}\n보유 기구 전체: {eq_names}"
    if gym_data.get("notes"):
        summary += f"\n특이사항: {gym_data['notes']}"

    documents.append(summary)
    metadatas.append({"user_id": user_id, "doc_type": "summary"})
    ids.append(f"{user_id}_summary")

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


# ── 공개 API ─────────────────────────────────────────────────────────────────

def save_gym_to_vector_db(user_id: int, gym_data: dict):
    """헬스장 기구 정보를 임베딩 후 저장합니다 (API 또는 ChromaDB)."""
    if _use_api():
        import requests
        payload = {"user_id": user_id, "gym_data": gym_data}
        resp = requests.post(_api_url("/gym/index"), json=payload, headers=_api_headers(), timeout=30)
        resp.raise_for_status()
    else:
        _chroma_save(user_id, gym_data)


def retrieve_gym_context(user_id: int) -> str:
    """해당 사용자의 헬스장 기구 정보를 프롬프트용 텍스트로 반환합니다."""
    if _use_api():
        try:
            import requests
            resp = requests.get(_api_url(f"/gym/retrieve/{user_id}"), headers=_api_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json().get("context", "")
        except Exception:
            return ""
    else:
        try:
            collection = _get_collection()
            results = collection.get(where={"user_id": user_id})
            if not results["documents"]:
                return ""
            paired = list(zip(results["metadatas"], results["documents"]))
            paired.sort(key=lambda x: 0 if x[0].get("doc_type") == "summary" else 1)
            return "\n".join(doc for _, doc in paired)
        except Exception:
            return ""


def get_gym_profile_from_api(user_id: int) -> dict | None:
    """API 모드일 때 저장된 헬스장 원본 데이터를 반환합니다."""
    if not _use_api():
        return None
    try:
        import requests
        resp = requests.get(_api_url(f"/gym/data/{user_id}"), headers=_api_headers(), timeout=10)
        resp.raise_for_status()
        body = resp.json()
        return body.get("gym_data") if body.get("has_data") else None
    except Exception:
        return None


def has_gym_data(user_id: int) -> bool:
    """해당 사용자의 헬스장 데이터 존재 여부를 확인합니다."""
    if _use_api():
        try:
            import requests
            resp = requests.get(_api_url(f"/gym/exists/{user_id}"), headers=_api_headers(), timeout=10)
            resp.raise_for_status()
            return resp.json().get("exists", False)
        except Exception:
            return False
    else:
        try:
            collection = _get_collection()
            results = collection.get(where={"user_id": user_id})
            return len(results["ids"]) > 0
        except Exception:
            return False
