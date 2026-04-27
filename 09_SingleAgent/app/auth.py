"""Auth — JWT 인증 모듈 (08_FitStep_API MySQL users 테이블 연동)"""

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.db import get_connection

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fitstep-single-agent-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _hash_pw(pw: str) -> str:
    """08_FitStep_API와 동일한 sha256 해시."""
    return hashlib.sha256(pw.encode()).hexdigest()


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """users 테이블에서 username + sha256(password)로 사용자를 조회합니다."""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, username, age, gender, height_cm, weight_kg, "
            "fitness_level, goal, health_notes, injury_tags "
            "FROM users WHERE username = %s AND password_hash = %s",
            (username, _hash_pw(password)),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception:
        return None


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, name, username, age, gender, height_cm, weight_kg, "
            "fitness_level, goal, health_notes, injury_tags "
            "FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception:
        user = None

    if user is None:
        raise credentials_exception
    return user
