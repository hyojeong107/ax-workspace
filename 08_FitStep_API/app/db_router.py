"""DB 중계 라우터 — users / routines / workout_logs"""

import hashlib
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from app.auth import verify_api_key
from app.db import get_connection
from app.db_schemas import (
    UserCreate, UserLogin, UserOut, UserWeightUpdate,
    RoutineSave, RoutineOut,
    LogSave, LogOut,
)

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
