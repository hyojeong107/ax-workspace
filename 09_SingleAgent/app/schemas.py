"""Schemas — Pydantic request/response models"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="사용자 프로필 (나이, 성별, BMI 등)")
    gym_data: Optional[Dict[str, Any]] = Field(None, description="헬스장 기구 정보")
    conversation_history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="이전 대화 기록")


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str = Field(..., description="에이전트 최종 답변")
    complete: bool = Field(..., description="커리큘럼 생성 완료 여부")
    curriculum: Optional[Dict[str, Any]] = Field(None, description="생성된 커리큘럼 JSON")
    validation_result: Optional[ValidationResult] = Field(None, description="커리큘럼 검증 결과")
    tool_calls_made: List[str] = Field(default_factory=list, description="호출된 도구 목록")
