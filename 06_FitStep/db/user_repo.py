# 사용자 데이터 저장/조회 함수 모음
# MySQL은 ? 대신 %s 를 플레이스홀더로 사용합니다

from db.database import get_connection

def save_user(name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes):
    """새 사용자를 DB에 저장하고 생성된 ID를 반환합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes))
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return user_id

def get_user(user_id):
    """ID로 사용자 정보를 조회합니다."""
    conn = get_connection()
    # dictionary=True: 컬럼 이름으로 접근 가능 (예: user["name"])
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user

def get_all_users():
    """저장된 모든 사용자 목록을 반환합니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, fitness_level, goal FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users

def update_user_weight(user_id, new_weight_kg):
    """사용자의 체중을 업데이트합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET weight_kg = %s WHERE id = %s", (new_weight_kg, user_id))
    conn.commit()
    cursor.close()
    conn.close()
