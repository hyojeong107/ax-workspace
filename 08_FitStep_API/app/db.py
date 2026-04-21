"""DB 연결 및 초기화"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "mysql"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "fitstep"),
        charset="utf8mb4",
    )


def init_db():
    base = mysql.connector.connect(
        host=os.getenv("DB_HOST", "mysql"),
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

    conn = get_connection()
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

    conn.commit()
    cursor.close()
    conn.close()
