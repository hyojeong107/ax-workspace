"""API Client — FastAPI 백엔드와 통신"""

import os
import requests
import streamlit as st
from typing import Any, Dict, List, Optional

BASE_URL = os.getenv("AGENT_API_URL", "http://localhost:8000")
_token_cache: Optional[str] = None


def _headers() -> Dict[str, str]:
    token = st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def health_check() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def login(username: str, password: str) -> Optional[str]:
    try:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        return None
    except Exception:
        return None


def verify_token() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/auth/verify", headers=_headers(), timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def chat(
    message: str,
    user_profile: Optional[Dict] = None,
    gym_data: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        r = requests.post(
            f"{BASE_URL}/chat",
            json={"message": message, "user_profile": user_profile, "gym_data": gym_data},
            headers=_headers(),
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
        return {"error": r.json().get("detail", f"HTTP {r.status_code}")}
    except Exception as e:
        return {"error": str(e)}


def list_curricula(limit: int = 10) -> Optional[Dict]:
    try:
        r = requests.get(f"{BASE_URL}/curricula?limit={limit}", headers=_headers(), timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def download_curriculum_url(curriculum_id: int) -> str:
    return f"{BASE_URL}/curricula/{curriculum_id}/download"


def delete_curriculum(curriculum_id: int) -> bool:
    try:
        r = requests.delete(f"{BASE_URL}/curricula/{curriculum_id}", headers=_headers(), timeout=10)
        return r.status_code == 200
    except Exception:
        return False
