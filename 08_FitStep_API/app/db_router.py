"""DB 중계 라우터 — users / routines / workout_logs"""

import hashlib
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import verify_api_key
from app.db import get_connection
from app.db_schemas import (
    UserCreate, UserLogin, UserOut, UserWeightUpdate, UserProfileUpdate,
    RoutineSave, RoutineOut,
    LogSave,
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


@router.get("/users/exists")
def username_exists(username: str = Query(...)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    found = cursor.fetchone() is not None
    cursor.close(); conn.close()
    return {"exists": found}


@router.get("/users", response_model=list[UserOut])
def get_all_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close(); conn.close()
    return users


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


@router.patch("/users/{user_id}/profile", response_model=UserOut)
def update_profile(user_id: int, body: UserProfileUpdate):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="업데이트할 필드가 없습니다.")
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id]
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"UPDATE users SET {set_clause} WHERE id = %s", values)
    conn.commit()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close(); conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return user


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
    """RapidAPI ExerciseDB 전체 운동 목록을 페이지네이션으로 가져와 DB에 upsert (exercise_id 포함)"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not set")

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }

    all_exercises = []
    limit = 500
    offset = 0
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            while True:
                resp = await client.get(
                    f"https://exercisedb.p.rapidapi.com/exercises?limit={limit}&offset={offset}",
                    headers=headers
                )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                all_exercises.extend(batch)
                if len(batch) < limit:
                    break
                offset += limit
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RapidAPI error: {e}")

    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    for ex in all_exercises:
        name_en = ex.get("name", "").strip()
        body_part = ex.get("bodyPart", "")
        exercise_id = ex.get("id", "")
        if not name_en:
            continue
        # name은 한글명 자리 — sync 데이터는 한글명이 없으므로 name_en 기준으로 UNIQUE 관리
        # name 컬럼에 영문을 넣지 않도록 name_en만 upsert 키로 사용
        cursor.execute("""
            INSERT INTO exercises (name, name_en, body_part, exercise_id, synced)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                body_part   = VALUES(body_part),
                exercise_id = VALUES(exercise_id),
                synced      = 1
        """, (name_en, name_en, body_part, exercise_id))
        inserted += 1

    conn.commit()
    cursor.close(); conn.close()
    return {"synced": inserted, "total_fetched": len(all_exercises)}


@router.get("/exercises/list")
def get_exercise_list():
    """GPT 프롬프트용 운동 목록 반환 (name_en + body_part)"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name_en, body_part FROM exercises WHERE synced = 1 ORDER BY name_en")
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return rows


GIF_DIR = os.path.join(os.path.dirname(__file__), "static", "gifs")
os.makedirs(GIF_DIR, exist_ok=True)


async def _download_and_cache_gif(exercise_db_id: int, exercise_id: str, rapidapi_key: str) -> str | None:
    """RapidAPI에서 GIF를 다운로드해 로컬에 저장하고 정적 경로를 DB에 기록 후 반환"""
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"https://exercisedb.p.rapidapi.com/image?exerciseId={exercise_id}&resolution=360",
                headers=headers
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/gif")
            ext = "gif" if "gif" in content_type else "webp"
            filename = f"{exercise_id}.{ext}"
            filepath = os.path.join(GIF_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(resp.content)

        static_url = f"/static/gifs/{filename}"
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE exercises SET gif_url = %s WHERE id = %s", (static_url, exercise_db_id))
        conn.commit()
        cursor.close(); conn.close()
        return static_url
    except Exception as e:
        print(f"GIF 다운로드 실패 (exerciseId={exercise_id}): {e}")
        return None


@router.get("/exercises/gif")
async def get_exercise_gif(
    name_kr: str = Query(..., description="운동명(한글)"),
    name_en: str = Query(None, description="운동명(영문)")
):
    """
    1) DB에 gif_url(로컬 캐시) 있으면 바로 반환 — RapidAPI 호출 없음
    2) exercise_id 있으면 GIF 다운로드 → 로컬 저장 → gif_url DB 저장
    3) exercise_id도 없으면 RapidAPI name 검색 → exercise_id 획득 → 2번 수행
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, gif_url, name_en, exercise_id FROM exercises WHERE name = %s", (name_kr,))
    exercise = cursor.fetchone()

    if not exercise:
        cursor.execute(
            "INSERT INTO exercises (name, name_en, synced) VALUES (%s, %s, 0)",
            (name_kr, name_en)
        )
        conn.commit()
        exercise = {"id": cursor.lastrowid, "gif_url": None, "name_en": name_en, "exercise_id": None}

    # 로컬 캐시 파일 있으면 바로 반환 (API 호출 없음)
    if exercise["gif_url"]:
        cursor.close(); conn.close()
        return {"gif_url": exercise["gif_url"]}

    effective_name_en = name_en or exercise.get("name_en")
    cursor.close(); conn.close()

    if not effective_name_en:
        return {"gif_url": None}

    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        return {"gif_url": None}

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }

    exercise_id = exercise.get("exercise_id")

    # exercise_id 없으면 name 검색으로 획득
    # 전체 이름 검색 실패 시 앞 단어를 줄여가며 재시도 (예: "smith machine squat" → "smith squat" → "smith")
    if not exercise_id:
        words = effective_name_en.lower().split()
        # 시도할 키워드 목록: 전체 → 앞뒤 단어 조합 → 첫 단어만
        candidates = [effective_name_en.lower()]
        if len(words) >= 3:
            # "machine" 같은 중간 수식어 제거: 첫 단어 + 마지막 단어
            candidates.append(f"{words[0]} {words[-1]}")
        if len(words) >= 2:
            candidates.append(words[0])

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for candidate in candidates:
                    encoded = quote(candidate)
                    resp = await client.get(
                        f"https://exercisedb.p.rapidapi.com/exercises/name/{encoded}?limit=1&offset=0",
                        headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        exercise_id = data[0].get("id")
                        matched_name = data[0].get("name", effective_name_en)
                        print(f"RapidAPI: '{effective_name_en}' → '{candidate}' 검색 성공 (id={exercise_id}, matched='{matched_name}')")
                        conn2 = get_connection()
                        cur2 = conn2.cursor()
                        cur2.execute(
                            "UPDATE exercises SET exercise_id = %s, name_en = %s WHERE id = %s",
                            (exercise_id, matched_name, exercise["id"])
                        )
                        conn2.commit()
                        cur2.close(); conn2.close()
                        break
                    print(f"RapidAPI: '{candidate}' 검색 결과 없음, 다음 시도...")
        except Exception as e:
            print(f"RapidAPI name search error: {e}")

    if not exercise_id:
        return {"gif_url": None}

    # GIF 다운로드 → 로컬 저장 → DB gif_url 업데이트 (API 1회)
    gif_url = await _download_and_cache_gif(exercise["id"], exercise_id, rapidapi_key)
    return {"gif_url": gif_url}


from fastapi.responses import StreamingResponse

gif_proxy_router = APIRouter()

@gif_proxy_router.get("/gif-proxy")
async def gif_proxy(exerciseId: str = Query(...)):
    """로컬에 캐시 파일이 없는 경우를 위한 폴백 프록시 (인증 불필요)"""
    rapidapi_key = os.getenv("RAPIDAPI_KEY")
    if not rapidapi_key:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not set")

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "exercisedb.p.rapidapi.com"
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://exercisedb.p.rapidapi.com/image?exerciseId={exerciseId}&resolution=360",
                headers=headers
            )
            resp.raise_for_status()
            return StreamingResponse(
                iter([resp.content]),
                media_type=resp.headers.get("content-type", "image/gif")
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
