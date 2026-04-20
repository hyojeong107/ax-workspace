"""06_3. Auth — API Key 인증 미들웨어"""

import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """요청 헤더의 X-API-Key 를 환경변수 RAG_API_KEY 와 비교합니다."""
    expected = os.getenv("RAG_API_KEY")
    if not expected:
        return "no-auth"
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
