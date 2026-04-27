"""DB 연결 및 초기화"""

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
            pool_name="fitstep_pool",
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
        database=os.getenv("DB_NAME", "fitstep"),
        charset="utf8mb4",
    )
    cursor = conn.cursor()

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
            created_at    DATETIME DEFAULT NOW()
        )
    """)

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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            name       VARCHAR(100) NOT NULL UNIQUE,
            name_en    VARCHAR(150),
            category   VARCHAR(50),
            body_part  VARCHAR(50),
            gif_url    VARCHAR(512) DEFAULT NULL,
            synced     TINYINT(1) DEFAULT 0,
            created_at DATETIME DEFAULT NOW()
        )
    """)

    # injury_tags 컬럼 추가 (없으면 추가, 있으면 무시)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN injury_tags VARCHAR(200) DEFAULT NULL")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN injury_tags VARCHAR(200) DEFAULT NULL")
    except Exception:
        pass

    for col, definition in [
        ("gif_url", "VARCHAR(512) DEFAULT NULL"),
        ("body_part", "VARCHAR(50)"),
        ("synced", "TINYINT(1) DEFAULT 0"),
        ("exercise_id", "VARCHAR(20) DEFAULT NULL"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE exercises ADD COLUMN {col} {definition}")
        except Exception:
            pass

    # 성능 인덱스 — 이미 존재하면 조용히 무시
    for idx_sql in [
        "CREATE INDEX idx_wl_user_logged ON workout_logs(user_id, logged_at)",
        "CREATE INDEX idx_wl_user_exercise ON workout_logs(user_id, exercise_name)",
        "CREATE INDEX idx_rt_user_date ON routines(user_id, routine_date)",
    ]:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass

    conn.commit()
    cursor.close()
    conn.close()
