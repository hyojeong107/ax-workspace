"""Main — FastAPI 진입점"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from app.schemas import IndexRequest, IndexResponse, RetrieveResponse, ExistsResponse, GymDataResponse, ChatRequest, ChatResponse
from app.auth import verify_api_key
from app.indexing import index_gym
from app.retrieval import retrieve_context, gym_exists, get_gym_data, retrieve_fitness_context, retrieve_exercise_recommendation
from app.db import init_db
from app.db_router import router as db_router, gif_proxy_router
import os
from openai import OpenAI

app = FastAPI(
    title="FitStep API",
    description="FitStep RAG + DB 중계 서비스",
    version="2.0.0",
)

GIF_DIR = os.path.join(os.path.dirname(__file__), "static", "gifs")
os.makedirs(GIF_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(db_router, prefix="/db")
app.include_router(gif_proxy_router, prefix="/db/exercises")


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


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def post_chat(body: ChatRequest):
    """사용자 메시지에 RAG 컨텍스트를 주입해 AI 답변을 반환합니다."""
    # RAG 컨텍스트 수집
    gym_context = retrieve_context(body.user_id)

    fitness_context = ""
    if body.age and body.gender and body.bmi:
        fitness_context = retrieve_fitness_context(body.age, body.gender, body.bmi)

    exercise_context = ""
    if body.age_group and body.gender and body.bmi_grade:
        exercise_context = retrieve_exercise_recommendation(body.age_group, body.gender, body.bmi_grade)

    # 시스템 프롬프트 구성
    context_parts = []
    if gym_context:
        context_parts.append(f"[사용자 헬스장 정보]\n{gym_context}")
    if fitness_context:
        context_parts.append(f"[유사 체력측정 사례]\n{fitness_context}")
    if exercise_context:
        context_parts.append(f"[추천 운동 정보]\n{exercise_context}")

    system_prompt = "당신은 개인 맞춤형 운동 처방 전문가입니다. 아래 컨텍스트를 바탕으로 사용자에게 맞는 운동 조언을 제공하세요.\n\n"
    if context_parts:
        system_prompt += "\n\n".join(context_parts)
    else:
        system_prompt += "사용자의 헬스장 및 체력 데이터가 없습니다. 일반적인 운동 조언을 제공하세요."

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": body.message},
            ],
            temperature=0.7,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(user_id=body.user_id, answer=answer)
