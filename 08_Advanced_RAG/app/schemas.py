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
