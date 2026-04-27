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


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    check_summary: Dict[str, bool] = Field(default_factory=dict)


class SpecialistsCalled(BaseModel):
    strength: bool = False
    cardio: bool = False
    rehab: bool = False
    reason: str = ""


class ChatResponse(BaseModel):
    reply: str = Field(..., description="파이프라인 요약 메시지")
    complete: bool = Field(..., description="커리큘럼 생성 완료 여부")
    curriculum: Optional[Dict[str, Any]] = Field(None, description="생성된 커리큘럼 JSON")
    validation_result: Optional[ValidationResult] = Field(None, description="검증 결과")
    matched_exercises: Optional[Dict[str, Any]] = Field(None, description="기구별 운동 매핑 결과")
    specialists_called: Optional[SpecialistsCalled] = Field(None, description="호출된 전문가 에이전트")
    pipeline_log: List[str] = Field(default_factory=list, description="파이프라인 단계별 처리 로그")


# ── Curriculum Storage ────────────────────────────────────────────────────────

class CurriculumSaveRequest(BaseModel):
    curriculum: Dict[str, Any] = Field(..., description="저장할 커리큘럼 JSON")
    label: Optional[str] = Field(None, description="커리큘럼 이름/레이블 (선택)")


class CurriculumListItem(BaseModel):
    id: int
    label: Optional[str]
    created_at: str
    specialists_used: List[str] = Field(default_factory=list)
    total_days: int = 0
    is_valid: bool = True


class CurriculumListResponse(BaseModel):
    items: List[CurriculumListItem]
    total: int
