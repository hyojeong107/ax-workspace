"""DB API용 Pydantic 스키마"""

from typing import Optional, List
from pydantic import BaseModel


# ── User ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    fitness_level: str
    goal: str
    health_notes: Optional[str] = ""


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    username: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    fitness_level: Optional[str]
    goal: Optional[str]
    health_notes: Optional[str]
    injury_tags: Optional[str] = None


class UserWeightUpdate(BaseModel):
    weight_kg: float


class UserProfileUpdate(BaseModel):
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    age: Optional[int] = None
    fitness_level: Optional[str] = None
    goal: Optional[str] = None
    health_notes: Optional[str] = None
    injury_tags: Optional[str] = None


# ── Routine ───────────────────────────────────────────────────────────────────

class RoutineSave(BaseModel):
    user_id: int
    exercises_json: str
    ai_advice: str


class RoutineOut(BaseModel):
    id: int
    user_id: int
    routine_date: str
    exercises_json: str
    ai_advice: Optional[str]
    is_completed: int


# ── Workout Log ───────────────────────────────────────────────────────────────

class LogSave(BaseModel):
    user_id: int
    routine_id: int
    exercise_name: str
    sets_done: int
    reps_done: int
    weight_kg: float
    note: Optional[str] = ""


class LogOut(BaseModel):
    exercise_name: str
    sets_done: int
    reps_done: int
    weight_kg: float
    note: Optional[str]
    log_date: str
