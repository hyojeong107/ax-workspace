"""DB 중계 라우터 — users / routines / workout_logs"""

import hashlib
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import verify_api_key
from app.db import get_connection
from app.db_schemas import (
    UserCreate, UserLogin, UserOut, UserWeightUpdate,
    RoutineSave, RoutineOut,
    LogSave, LogOut,
)
import httpx
from urllib.parse import quote
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Users ─────────────────────────────────────────────────────────────────────

@router.post("/users", response_model=UserOut)
def create_user(body: UserCreate):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id FROM users WHERE username = %s", (body.username,)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")

    cursor.execute("""
        INSERT INTO users
            (name, username, password_hash, age, gender, height_cm, weight_kg,
             fitness_level, goal, health_notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (body.name, body.username, _hash_pw(body.password),
          body.age, body.gender, body.height_cm, body.weight_kg,
          body.fitness_level, body.goal, body.health_notes))
    conn.commit()
    user_id = cursor.lastrowid
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    return user


@router.post("/users/login", response_model=UserOut)
def login(body: UserLogin):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username = %s AND password_hash = %s",
        (body.username, _hash_pw(body.password)),
    )
    user = cursor.fetchone()
    cursor.close(); conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다.")
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user


@router.get("/users", response_model=list[UserOut])
def get_all_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close(); conn.close()
    return users


@router.patch("/users/{user_id}/weight")
def update_weight(user_id: int, body: UserWeightUpdate):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET weight_kg = %s WHERE id = %s",
        (body.weight_kg, user_id)
    )
    conn.commit()
    cursor.close(); conn.close()
    return {"ok": True}


# ── Routines ──────────────────────────────────────────────────────────────────

@router.post("/routines", response_model=RoutineOut)
def save_routine(body: RoutineSave):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    import json
    try:
        # 루틴 내의 운동들을 exercises 테이블과 동기화 (없으면 INSERT)
        exercises = json.loads(body.exercises_json)
        for ex in exercises:
            name = ex.get("name")
            name_en = ex.get("name_en")
            category = ex.get("category")
            if name:
                cursor.execute("SELECT id, name_en FROM exercises WHERE name = %s", (name,))
                existing = cursor.fetchone()
                try:
                    if not existing:
                        cursor.execute(
                            "INSERT INTO exercises (name, name_en, category) VALUES (%s, %s, %s)",
                            (name, name_en, category)
                        )
                    elif not existing["name_en"] and name_en:
                        cursor.execute(
                            "UPDATE exercises SET name_en = %s, category = %s WHERE name = %s",
                            (name_en, category, name)
                        )
                except Exception as e:
                    print("운동 정보 동기화 에러:", e)
    except Exception as e:
        print("JSON parse error for exercises:", e)
        
    cursor.execute("""
        INSERT INTO routines (user_id, routine_date, exercises_json, ai_advice)
        VALUES (%s, %s, %s, %s)
    """, (body.user_id, date.today().isoformat(), body.exercises_json, body.ai_advice))
    conn.commit()
    routine_id = cursor.lastrowid
    cursor.execute("SELECT * FROM routines WHERE id = %s", (routine_id,))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    row["routine_date"] = str(row["routine_date"])
    return row


@router.get("/routines/today/{user_id}", response_model=RoutineOut | None)
def get_today_routine(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM routines
        WHERE user_id = %s AND routine_date = %s
        ORDER BY id DESC LIMIT 1
    """, (user_id, date.today().isoformat()))
    row = cursor.fetchone()
    cursor.close(); conn.close()
    if row:
        row["routine_date"] = str(row["routine_date"])
    return row


@router.delete("/routines/today/{user_id}")
def delete_today_routine(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM workout_logs WHERE routine_id IN "
        "(SELECT id FROM routines WHERE user_id=%s AND routine_date=%s)",
        (user_id, date.today().isoformat())
    )
    cursor.execute(
        "DELETE FROM routines WHERE user_id=%s AND routine_date=%s",
        (user_id, date.today().isoformat())
    )
    conn.commit()
    cursor.close(); conn.close()
    return {"ok": True}


@router.patch("/routines/{routine_id}/complete")
def complete_routine(routine_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE routines SET is_completed = 1 WHERE id = %s", (routine_id,)
    )
    conn.commit()
    cursor.close(); conn.close()
    return {"ok": True}


# ── Workout Logs ──────────────────────────────────────────────────────────────

@router.post("/logs")
def save_log(body: LogSave):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workout_logs
            (user_id, routine_id, exercise_name, sets_done, reps_done, weight_kg, note)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (body.user_id, body.routine_id, body.exercise_name,
          body.sets_done, body.reps_done, body.weight_kg, body.note))
    conn.commit()
    cursor.close(); conn.close()
    return {"ok": True}


@router.get("/logs/routine/{routine_id}/names")
def get_logged_names(routine_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT exercise_name FROM workout_logs WHERE routine_id = %s", (routine_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return [r["exercise_name"] for r in rows]


@router.get("/logs/recent/{user_id}")
def get_recent_logs(user_id: int, limit: int = 20):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name, sets_done, reps_done, weight_kg, note,
               DATE(logged_at) AS log_date
        FROM workout_logs
        WHERE user_id = %s
        ORDER BY logged_at DESC LIMIT %s
    """, (user_id, limit))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    for r in rows:
        r["log_date"] = str(r["log_date"])
    return rows


@router.get("/logs/recent-exercises/{user_id}")
def get_recent_exercises(user_id: int, days: int = 7):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name FROM workout_logs
        WHERE user_id = %s AND logged_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY exercise_name ORDER BY MAX(logged_at) DESC LIMIT 10
    """, (user_id, days))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return [r["exercise_name"] for r in rows]


@router.get("/logs/stats/{user_id}")
def get_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM routines WHERE user_id=%s AND is_completed=1", (user_id,)
    )
    completed_routines = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM workout_logs WHERE user_id=%s", (user_id,)
    )
    total_logs = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(DISTINCT DATE(logged_at)) AS cnt FROM workout_logs WHERE user_id=%s", (user_id,)
    )
    active_days = cursor.fetchone()["cnt"]

    cursor.execute("""
        SELECT DISTINCT DATE(logged_at) AS d FROM workout_logs
        WHERE user_id=%s ORDER BY d DESC
    """, (user_id,))
    from datetime import timedelta
    dates = [row["d"] for row in cursor.fetchall()]
    today = date.today()
    streak = sum(1 for i, d in enumerate(dates) if d == today - timedelta(days=i))

    cursor.close(); conn.close()
    return {
        "completed_routines": completed_routines,
        "total_logs": total_logs,
        "active_days": active_days,
        "streak": streak,
    }


@router.get("/logs/progression/{user_id}")
def get_progression(user_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name, COUNT(*) AS total_sessions,
               MAX(weight_kg) AS max_weight, MAX(reps_done) AS max_reps,
               MAX(logged_at) AS last_logged
        FROM workout_logs WHERE user_id=%s
        GROUP BY exercise_name ORDER BY total_sessions DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    for r in rows:
        r["last_logged"] = str(r["last_logged"])
    return rows


@router.get("/logs/exercise-history/{user_id}/{exercise_name}")
def get_exercise_history(user_id: int, exercise_name: str, limit: int = 5):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sets_done, reps_done, weight_kg, logged_at
        FROM workout_logs
        WHERE user_id=%s AND exercise_name=%s
        ORDER BY logged_at DESC LIMIT %s
    """, (user_id, exercise_name, limit))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    for r in rows:
        r["logged_at"] = str(r["logged_at"])
    return rows

# ── Exercises ────────────────────────────────────────────────────────────────

@router.post("/exercises/sync")
async def sync_exercises():
    """RapidAPI ExerciseDB에서 전체 운동 목록을 가져와 DB에 upsert"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not set")

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }

    all_exercises = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://exercisedb.p.rapidapi.com/exercises?limit=1500&offset=0",
                headers=headers
            )
            resp.raise_for_status()
            all_exercises = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RapidAPI error: {e}")

    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    for ex in all_exercises:
        name_en = ex.get("name", "").strip()
        body_part = ex.get("bodyPart", "")
        gif_url = ex.get("gifUrl", "")
        if not name_en:
            continue
        # name_en 기준으로 upsert (한글명은 없으므로 name=name_en으로 임시 저장, synced=1)
        cursor.execute("""
            INSERT INTO exercises (name, name_en, body_part, gif_url, synced)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                name_en  = VALUES(name_en),
                body_part = VALUES(body_part),
                gif_url  = VALUES(gif_url),
                synced   = 1
        """, (name_en, name_en, body_part, gif_url))
        inserted += 1

    conn.commit()
    cursor.close(); conn.close()
    return {"synced": inserted}


@router.get("/exercises/list")
def get_exercise_list():
    """GPT 프롬프트용 운동 목록 반환 (name_en + body_part)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name_en, body_part FROM exercises WHERE synced = 1 ORDER BY name_en")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


@router.get("/exercises/gif")
async def get_exercise_gif(
    name_kr: str = Query(..., description="운동명(한글)"),
    name_en: str = Query(None, description="운동명(영문, RapidAPI와 정확히 일치하는 이름)")
):
    """
    synced=1 운동은 DB에 gif_url이 이미 있음 → 바로 반환.
    루틴 저장 시 등록된 신규 운동(synced=0)은 name_en으로 RapidAPI 조회 후 캐싱.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, gif_url, synced, name_en FROM exercises WHERE name = %s", (name_kr,))
    exercise = cursor.fetchone()

    if not exercise:
        # 아직 exercises 테이블에 없으면 등록
        cursor.execute(
            "INSERT INTO exercises (name, name_en, synced) VALUES (%s, %s, 0)",
            (name_kr, name_en)
        )
        conn.commit()
        exercise = {"id": cursor.lastrowid, "gif_url": None, "synced": 0, "name_en": name_en}

    # gif_url이 이미 있으면 바로 반환 (synced=1 포함)
    if exercise["gif_url"]:
        cursor.close(); conn.close()
        return {"gif_url": exercise["gif_url"]}

    # name_en이 없으면 검색 불가
    effective_name_en = name_en or exercise.get("name_en")
    if not effective_name_en:
        cursor.close(); conn.close()
        return {"gif_url": None}

    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        cursor.close(); conn.close()
        return {"gif_url": None}

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }

    gif_url = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            encoded = quote(effective_name_en.lower())
            resp = await client.get(
                f"https://exercisedb.p.rapidapi.com/exercises/name/{encoded}?limit=1&offset=0",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                gif_url = data[0].get("gifUrl")
            else:
                print(f"RapidAPI: no result for '{effective_name_en}'")
    except Exception as e:
        print(f"RapidAPI fetch error: {e}")

    if gif_url:
        cursor.execute(
            "UPDATE exercises SET gif_url = %s, name_en = %s WHERE id = %s",
            (gif_url, effective_name_en, exercise["id"])
        )
        conn.commit()

    cursor.close(); conn.close()
    return {"gif_url": gif_url}
