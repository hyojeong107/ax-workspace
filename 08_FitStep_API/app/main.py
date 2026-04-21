"""Main — FastAPI 진입점"""

from fastapi import FastAPI, Depends, HTTPException
from app.schemas import IndexRequest, IndexResponse, RetrieveResponse, ExistsResponse, GymDataResponse
from app.auth import verify_api_key
from app.indexing import index_gym
from app.retrieval import retrieve_context, gym_exists, get_gym_data
from app.db import init_db
from app.db_router import router as db_router

app = FastAPI(
    title="FitStep API",
    description="FitStep RAG + DB 중계 서비스",
    version="2.0.0",
)

app.include_router(db_router, prefix="/db")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/gym/index", response_model=IndexResponse, dependencies=[Depends(verify_api_key)])
def post_index(body: IndexRequest):
    """헬스장 기구 정보를 임베딩 후 ChromaDB에 저장합니다."""
    try:
        doc_count = index_gym(body.user_id, body.gym_data)
        return IndexResponse(
            success=True,
            message="인덱싱 완료",
            user_id=body.user_id,
            doc_count=doc_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gym/retrieve/{user_id}", response_model=RetrieveResponse, dependencies=[Depends(verify_api_key)])
def get_retrieve(user_id: int):
    """사용자 헬스장 기구 정보를 프롬프트용 텍스트로 반환합니다."""
    context = retrieve_context(user_id)
    return RetrieveResponse(user_id=user_id, has_data=bool(context), context=context)


@app.get("/gym/exists/{user_id}", response_model=ExistsResponse, dependencies=[Depends(verify_api_key)])
def get_exists(user_id: int):
    """해당 사용자의 헬스장 데이터 존재 여부를 확인합니다."""
    return ExistsResponse(user_id=user_id, exists=gym_exists(user_id))


@app.get("/gym/data/{user_id}", response_model=GymDataResponse, dependencies=[Depends(verify_api_key)])
def get_data(user_id: int):
    """저장된 헬스장 기구 원본 데이터를 반환합니다 (Streamlit 폼 복원용)."""
    data = get_gym_data(user_id)
    return GymDataResponse(user_id=user_id, has_data=data is not None, gym_data=data)
