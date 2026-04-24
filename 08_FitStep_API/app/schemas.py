"""06_2. Schemas — Pydantic request/response models"""

from typing import List, Optional
from pydantic import BaseModel, Field


class EquipmentItem(BaseModel):
    name: str = Field(..., description="기구 이름")
    quantity: Optional[int] = Field(None, description="수량")
    weight_range: Optional[str] = Field(None, description="무게 범위 (예: 5~100kg)")
    notes: Optional[str] = Field(None, description="기구별 비고")


class GymData(BaseModel):
    gym_name: str = Field(..., description="헬스장 이름")
    equipment: List[EquipmentItem] = Field(..., description="보유 기구 목록")
    notes: Optional[str] = Field(None, description="헬스장 전체 특이사항")


class IndexRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")
    gym_data: GymData


class IndexResponse(BaseModel):
    success: bool
    message: str
    user_id: int
    doc_count: int


class RetrieveResponse(BaseModel):
    user_id: int
    has_data: bool
    context: str


class ExistsResponse(BaseModel):
    user_id: int
    exists: bool


class GymDataResponse(BaseModel):
    user_id: int
    has_data: bool
    gym_data: Optional[GymData] = None


class ChatRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")
    message: str = Field(..., description="사용자 메시지")
    age: Optional[int] = Field(None, description="나이")
    gender: Optional[str] = Field(None, description="성별 (M/F)")
    bmi: Optional[float] = Field(None, description="BMI 수치")
    age_group: Optional[str] = Field(None, description="연령대 (예: 30대)")
    bmi_grade: Optional[str] = Field(None, description="BMI 등급 (예: 정상, 비만)")


class ChatResponse(BaseModel):
    user_id: int
    answer: str


class RagContextRequest(BaseModel):
    user_id: int
    age: int
    gender: str
    bmi: float
    age_group: str
    bmi_grade: str


class RagContextResponse(BaseModel):
    fitness_context: str
    exercise_context: str
    bmi_grade: str
    age_group: str
    is_high_risk: bool
