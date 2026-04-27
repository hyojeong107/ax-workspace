"""Indexing — ChromaDB 벡터 스토어 초기화 (08_FitStep_API 기반)"""

import os

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
FITNESS_COLLECTION = "fitness_measurement"
EXERCISE_COLLECTION = "exercise_recommendation"

_fitness_store: Chroma | None = None
_exercise_store: Chroma | None = None


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )


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
