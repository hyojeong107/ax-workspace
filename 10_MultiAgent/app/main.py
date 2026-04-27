"""Main — FastAPI 진입점 (Multi-Agent)"""

import json
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas import (
    ChatRequest, ChatResponse, LoginResponse,
    ValidationResult, SpecialistsCalled,
    CurriculumSaveRequest, CurriculumListItem, CurriculumListResponse,
)
from app.auth import authenticate_user, create_access_token, get_current_user
from app.agents.orchestrator import run_orchestrator
from app.db import init_db, get_connection

app = FastAPI(
    title="FitStep Multi-Agent API",
    description="멀티에이전트 (근력/유산소/재활/통합) 기반 운동 커리큘럼 생성 서비스",
    version="2.0.0",
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "mode": "multi-agent"}


# ── Auth ──────────────────────────────────────────────────────────────────────

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


# ── Multi-Agent Chat ──────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """멀티에이전트 파이프라인으로 커리큘럼을 생성합니다."""
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

    # BMI / 연령대 / BMI 등급 자동 계산 (미설정 시)
    if merged_profile.get("height_cm") and merged_profile.get("weight_kg"):
        h = merged_profile["height_cm"] / 100
        bmi = round(merged_profile["weight_kg"] / (h * h), 1)
        merged_profile.setdefault("bmi", bmi)

    age = merged_profile.get("age", 30)
    merged_profile.setdefault("age_group", f"{(age // 10) * 10}대")

    bmi_val = merged_profile.get("bmi", 22.0)
    if bmi_val < 18.5:
        bmi_grade = "저체중"
    elif bmi_val < 23:
        bmi_grade = "정상"
    elif bmi_val < 25:
        bmi_grade = "과체중"
    elif bmi_val < 30:
        bmi_grade = "비만"
    else:
        bmi_grade = "고도비만"
    merged_profile.setdefault("bmi_grade", bmi_grade)

    try:
        result = run_orchestrator(
            user_message=body.message,
            user_profile=merged_profile,
            gym_data=body.gym_data,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    vr_raw = result.get("validation_result", {})
    validation_result = ValidationResult(
        is_valid=vr_raw.get("is_valid", False),
        errors=vr_raw.get("errors", []),
        warnings=vr_raw.get("warnings", []),
        check_summary=vr_raw.get("check_summary", {}),
    ) if vr_raw else None

    sp_raw = result.get("specialists_called", {})
    specialists_called = SpecialistsCalled(
        strength=sp_raw.get("strength", False),
        cardio=sp_raw.get("cardio", False),
        rehab=sp_raw.get("rehab", False),
        reason=sp_raw.get("reason", ""),
    ) if sp_raw else None

    # 커리큘럼이 유효하면 자동 저장
    curriculum = result.get("curriculum")
    if curriculum and validation_result and validation_result.is_valid:
        _save_curriculum_to_db(
            user_id=current_user["id"],
            curriculum=curriculum,
            validation=vr_raw,
            specialists=sp_raw,
        )

    log = result.get("pipeline_log", [])
    reply = "\n".join(log) if log else "커리큘럼 생성이 완료되었습니다."

    return ChatResponse(
        reply=reply,
        complete=curriculum is not None and (validation_result is None or validation_result.is_valid),
        curriculum=curriculum,
        validation_result=validation_result,
        matched_exercises=result.get("matched_exercises"),
        specialists_called=specialists_called,
        pipeline_log=log,
    )


# ── Curriculum Storage ────────────────────────────────────────────────────────

def _save_curriculum_to_db(
    user_id: int,
    curriculum: dict,
    validation: dict,
    specialists: dict,
    label: str = None,
) -> int:
    specialists_str = ",".join(
        k for k, v in specialists.items() if v and k in ("strength", "cardio", "rehab")
    )
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO curricula
           (user_id, label, curriculum_json, specialists_used, total_days, is_valid, validation_json)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            user_id,
            label,
            json.dumps(curriculum, ensure_ascii=False),
            specialists_str,
            curriculum.get("total_days", 0),
            1 if validation.get("is_valid") else 0,
            json.dumps(validation, ensure_ascii=False),
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return new_id


@app.post("/curricula/save")
def save_curriculum(
    body: CurriculumSaveRequest,
    current_user: dict = Depends(get_current_user),
):
    """커리큘럼을 수동으로 저장합니다."""
    try:
        new_id = _save_curriculum_to_db(
            user_id=current_user["id"],
            curriculum=body.curriculum,
            validation={"is_valid": True},
            specialists={},
            label=body.label,
        )
        return {"id": new_id, "message": "저장 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/curricula", response_model=CurriculumListResponse)
def list_curricula(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """사용자의 커리큘럼 목록을 반환합니다."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, label, created_at, specialists_used, total_days, is_valid
               FROM curricula WHERE user_id = %s
               ORDER BY created_at DESC LIMIT %s""",
            (current_user["id"], limit),
        )
        rows = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) AS cnt FROM curricula WHERE user_id = %s", (current_user["id"],))
        total = cursor.fetchone()["cnt"]
        cursor.close()
        conn.close()

        items = [
            CurriculumListItem(
                id=r["id"],
                label=r["label"],
                created_at=str(r["created_at"]),
                specialists_used=[s for s in (r["specialists_used"] or "").split(",") if s],
                total_days=r["total_days"] or 0,
                is_valid=bool(r["is_valid"]),
            )
            for r in rows
        ]
        return CurriculumListResponse(items=items, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/curricula/{curriculum_id}/download")
def download_curriculum(
    curriculum_id: int,
    current_user: dict = Depends(get_current_user),
):
    """커리큘럼 JSON을 파일로 다운로드합니다."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT curriculum_json, label FROM curricula WHERE id = %s AND user_id = %s",
            (curriculum_id, current_user["id"]),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="커리큘럼을 찾을 수 없습니다.")

        filename = f"curriculum_{curriculum_id}.json"
        return Response(
            content=row["curriculum_json"],
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/curricula/{curriculum_id}")
def delete_curriculum(
    curriculum_id: int,
    current_user: dict = Depends(get_current_user),
):
    """커리큘럼을 삭제합니다."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM curricula WHERE id = %s AND user_id = %s",
            (curriculum_id, current_user["id"]),
        )
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        if affected == 0:
            raise HTTPException(status_code=404, detail="커리큘럼을 찾을 수 없습니다.")
        return {"message": "삭제 완료"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
