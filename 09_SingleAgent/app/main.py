"""Main — FastAPI 진입점 (Single Agent)"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas import ChatRequest, ChatResponse, LoginResponse, ValidationResult
from app.auth import authenticate_user, create_access_token, get_current_user
from app.agent import run_agent
from app.db import init_db

app = FastAPI(
    title="FitStep Single Agent API",
    description="OpenAI tool-calling(ReAct) 기반 단일 에이전트 운동 코치",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    token = create_access_token({"sub": user["username"]})
    return LoginResponse(access_token=token)


@app.get("/auth/verify")
def verify_token(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "valid": True}


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """단일 에이전트 대화 엔드포인트. ReAct 루프로 도구를 선택 호출해 커리큘럼을 생성합니다."""
    # DB에서 가져온 사용자 프로필을 요청 body보다 우선 사용
    db_profile = {
        "age": current_user.get("age"),
        "gender": current_user.get("gender"),
        "height_cm": current_user.get("height_cm"),
        "weight_kg": current_user.get("weight_kg"),
        "fitness_level": current_user.get("fitness_level"),
        "goal": current_user.get("goal"),
        "health_notes": current_user.get("health_notes"),
        "injury_tags": current_user.get("injury_tags"),
    }
    merged_profile = {**db_profile, **(body.user_profile or {})}
    try:
        result = run_agent(
            user_message=body.message,
            user_profile=merged_profile,
            gym_data=body.gym_data,
            conversation_history=body.conversation_history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    validation_result = None
    if result.get("validation_result"):
        vr = result["validation_result"]
        validation_result = ValidationResult(
            is_valid=vr.get("is_valid", False),
            errors=vr.get("errors", []),
            warnings=vr.get("warnings", []),
        )

    return ChatResponse(
        reply=result["reply"],
        complete=result["complete"],
        curriculum=result.get("curriculum"),
        validation_result=validation_result,
        tool_calls_made=result.get("tool_calls_made", []),
    )
