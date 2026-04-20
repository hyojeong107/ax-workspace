"""FastAPI 백엔드 클라이언트 — DB 관련 모든 호출을 여기서 담당"""

import os
import requests

def _base() -> str:
    return os.getenv("RAG_API_URL", "").rstrip("/")

def _h() -> dict:
    key = os.getenv("RAG_API_KEY", "")
    return {"X-API-Key": key} if key else {}

def _get(path, **params):
    r = requests.get(_base() + path, headers=_h(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def _post(path, body):
    r = requests.post(_base() + path, headers=_h(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()

def _patch(path, body=None):
    r = requests.patch(_base() + path, headers=_h(), json=body or {}, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Users ─────────────────────────────────────────────────────────────────────

def api_save_user(name, age, gender, height_cm, weight_kg,
                  fitness_level, goal, health_notes, username, password):
    return _post("/db/users", {
        "name": name, "username": username, "password": password,
        "age": age, "gender": gender, "height_cm": height_cm,
        "weight_kg": weight_kg, "fitness_level": fitness_level,
        "goal": goal, "health_notes": health_notes or "",
    })

def api_login(username, password):
    try:
        return _post("/db/users/login", {"username": username, "password": password})
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            return None
        raise

def api_get_user(user_id):
    return _get(f"/db/users/{user_id}")

def api_get_all_users():
    return _get("/db/users")

def api_username_exists(username):
    users = api_get_all_users()
    return any(u["username"] == username for u in users)

def api_update_weight(user_id, weight_kg):
    return _patch(f"/db/users/{user_id}/weight", {"weight_kg": weight_kg})


# ── Routines ──────────────────────────────────────────────────────────────────

def api_save_routine(user_id, exercises_json, ai_advice):
    return _post("/db/routines", {
        "user_id": user_id,
        "exercises_json": exercises_json,
        "ai_advice": ai_advice,
    })

def api_get_today_routine(user_id):
    return _get(f"/db/routines/today/{user_id}")

def api_complete_routine(routine_id):
    return _patch(f"/db/routines/{routine_id}/complete")


# ── Workout Logs ──────────────────────────────────────────────────────────────

def api_save_log(user_id, routine_id, exercise_name,
                 sets_done, reps_done, weight_kg, note):
    return _post("/db/logs", {
        "user_id": user_id, "routine_id": routine_id,
        "exercise_name": exercise_name, "sets_done": sets_done,
        "reps_done": reps_done, "weight_kg": weight_kg, "note": note or "",
    })

def api_get_logged_names(routine_id):
    return _get(f"/db/logs/routine/{routine_id}/names")

def api_get_recent_logs(user_id, limit=20):
    return _get(f"/db/logs/recent/{user_id}", limit=limit)

def api_get_recent_exercises(user_id, days=7):
    return _get(f"/db/logs/recent-exercises/{user_id}", days=days)

def api_get_stats(user_id):
    return _get(f"/db/logs/stats/{user_id}")

def api_get_progression(user_id):
    return _get(f"/db/logs/progression/{user_id}")

def api_get_exercise_history(user_id, exercise_name, limit=5):
    return _get(f"/db/logs/exercise-history/{user_id}/{exercise_name}", limit=limit)
