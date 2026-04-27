"""API Client — Single Agent 백엔드 HTTP 클라이언트"""

import os
import requests
from typing import Any, Dict, List, Optional

_BASE_URL = os.getenv("AGENT_API_URL", "http://localhost:8001")
_TOKEN: Optional[str] = None


def _headers() -> Dict[str, str]:
    if _TOKEN:
        return {"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def login(username: str, password: str) -> Optional[str]:
    """로그인 후 JWT 토큰을 반환합니다."""
    global _TOKEN
    try:
        resp = requests.post(
            f"{_BASE_URL}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            _TOKEN = resp.json().get("access_token")
            return _TOKEN
        return None
    except Exception:
        return None


def set_token(token: str):
    global _TOKEN
    _TOKEN = token


def verify_token() -> bool:
    try:
        resp = requests.get(f"{_BASE_URL}/auth/verify", headers=_headers(), timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def chat(
    message: str,
    user_profile: Optional[Dict[str, Any]] = None,
    gym_data: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Optional[Dict[str, Any]]:
    """에이전트에 메시지를 보내고 응답을 반환합니다."""
    try:
        payload = {
            "message": message,
            "user_profile": user_profile,
            "gym_data": gym_data,
            "conversation_history": conversation_history or [],
        }
        resp = requests.post(
            f"{_BASE_URL}/chat",
            json=payload,
            headers=_headers(),
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"오류 {resp.status_code}: {resp.text}"}
    except requests.Timeout:
        return {"error": "요청 시간 초과 (120초). 에이전트가 처리 중입니다."}
    except Exception as e:
        return {"error": str(e)}


def health_check() -> bool:
    try:
        resp = requests.get(f"{_BASE_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
