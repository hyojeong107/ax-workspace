# 데이터베이스 초기화 및 연결 관리 모듈 (MySQL 버전)
# .env 파일에서 접속 정보를 읽어 MySQL에 연결합니다

import mysql.connector
from dotenv import load_dotenv
import os

# .env 파일 로드 (OPENAI_API_KEY, DB_HOST 등을 환경변수로 읽어옴)
load_dotenv()

def get_connection():
    """MySQL 연결 객체를 반환합니다."""
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "fitstep"),
        # 한글 저장을 위한 인코딩 설정
        charset="utf8mb4",
    )
    return conn

def init_db():
    """앱 최초 실행 시 필요한 테이블을 생성합니다."""
    # DB가 없으면 먼저 생성 (database 파라미터 없이 연결)
    base_conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        charset="utf8mb4",
    )
    base_cursor = base_conn.cursor()
    db_name = os.getenv("DB_NAME", "fitstep")
    # DB가 없으면 생성, 있으면 무시
    base_cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    base_conn.commit()
    base_cursor.close()
    base_conn.close()

    # 이제 해당 DB에 연결해서 테이블 생성
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 사용자 프로필 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            name          VARCHAR(100) NOT NULL,
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

    # 2. 운동 종목 테이블 (앱 내 운동 라이브러리)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            name_en     VARCHAR(100),
            category    VARCHAR(50),
            difficulty  VARCHAR(20),
            equipment   VARCHAR(50),
            description TEXT
        )
    """)

    # 3. 추천 루틴 테이블
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

    # 4. 운동 완료 기록 테이블
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
