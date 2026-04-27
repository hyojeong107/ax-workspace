"""DB 연결 및 초기화 (curricula 테이블 추가)"""

import os
import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool
from dotenv import load_dotenv

load_dotenv()

_pool: MySQLConnectionPool | None = None


def _get_pool() -> MySQLConnectionPool:
    global _pool
    if _pool is None:
        _pool = MySQLConnectionPool(
            pool_name="fitstep_multi_pool",
            pool_size=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "fitstep"),
            charset="utf8mb4",
        )
    return _pool


def get_connection():
    return _get_pool().get_connection()


def init_db():
    base = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
    )
    cur = base.cursor()
    db_name = os.getenv("DB_NAME", "fitstep")
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    base.commit()
    cur.close()
    base.close()

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=db_name,
        charset="utf8mb4",
    )
    cursor = conn.cursor()

    # users 테이블 (09_SingleAgent와 동일 스키마 유지)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(100) NOT NULL,
            username      VARCHAR(50)  UNIQUE,
            password_hash VARCHAR(255),
            age           INT,
            gender        VARCHAR(10),
            height_cm     FLOAT,
            weight_kg     FLOAT,
            fitness_level VARCHAR(20),
            goal          VARCHAR(200),
            health_notes  TEXT,
            injury_tags   VARCHAR(200) DEFAULT NULL,
            created_at    DATETIME DEFAULT NOW()
        )
    """)

    # curricula 테이블 — 커리큘럼 결과 저장 (신규)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS curricula (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            user_id          INT NOT NULL,
            label            VARCHAR(200) DEFAULT NULL,
            curriculum_json  LONGTEXT NOT NULL,
            specialists_used VARCHAR(100) DEFAULT NULL,
            total_days       INT DEFAULT 0,
            is_valid         TINYINT(1) DEFAULT 1,
            validation_json  TEXT DEFAULT NULL,
            created_at       DATETIME DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # 기존 테이블들 (09와 호환)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            user_id        INT NOT NULL,
            routine_date   DATE NOT NULL,
            exercises_json TEXT,
            ai_advice      TEXT,
            is_completed   TINYINT(1) DEFAULT 0,
            created_at     DATETIME DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_logs (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            user_id       INT NOT NULL,
            routine_id    INT,
            exercise_name VARCHAR(100) NOT NULL,
            sets_done     INT,
            reps_done     INT,
            weight_kg     FLOAT,
            note          TEXT,
            logged_at     DATETIME DEFAULT NOW(),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (routine_id) REFERENCES routines(id)
        )
    """)

    for idx_sql in [
        "CREATE INDEX idx_curricula_user ON curricula(user_id, created_at)",
        "CREATE INDEX idx_wl_user_logged ON workout_logs(user_id, logged_at)",
        "CREATE INDEX idx_rt_user_date ON routines(user_id, routine_date)",
    ]:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass

    conn.commit()
    cursor.close()
    conn.close()
