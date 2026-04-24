# 운동 루틴 추천 모듈
# 사용자 프로필을 바탕으로 OpenAI API에게 오늘의 루틴을 요청합니다

import os
import json
from datetime import date
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from db.database import get_connection
from modules.progression import build_progression_context
from rag.gym_rag import retrieve_gym_context

load_dotenv()
console = Console()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FITNESS_LABELS = {"beginner": "초보자", "intermediate": "중급자", "advanced": "고급자"}

def _build_prompt(user: dict, progression_context: str, gym_context: str) -> str:
    """사용자 정보 + 진행 분석 + 헬스장 기구 정보를 합쳐 AI 프롬프트를 만듭니다."""

    goals = user["goal"]
    level = FITNESS_LABELS.get(user["fitness_level"], user["fitness_level"])
    bmi   = round(user["weight_kg"] / ((user["height_cm"] / 100) ** 2), 1)

    prog_section = f"\n{progression_context}\n" if progression_context else ""

    # 헬스장 기구 정보가 있으면 "반드시 이 기구만 사용" 지시 섹션 추가
    if gym_context:
        gym_section = f"""
[헬스장 환경 - 아래 기구·시설만 사용하는 운동으로 구성해주세요]
{gym_context}
→ 위 목록에 없는 기구가 필요한 운동은 절대 추천하지 마세요.
→ 수량이 1개인 기구는 대기 없이 할 수 있는 대체 동작도 함께 고려해주세요.
"""
    else:
        gym_section = ""

    return f"""당신은 전문 헬스 트레이너입니다.
아래 사용자 정보를 바탕으로 오늘의 헬스장 운동 루틴을 추천해주세요.

[사용자 정보]
- 나이: {user['age']}세 / 성별: {user['gender']}
- 키: {user['height_cm']}cm / 몸무게: {user['weight_kg']}kg / BMI: {bmi}
- 체력 수준: {level}
- 운동 목표: {goals}
- 건강 주의사항: {user['health_notes'] or '없음'}
{prog_section}{gym_section}
[출력 규칙 - 반드시 지켜주세요]
1. 운동은 4~6개로 구성해주세요.
2. 목표가 여러 개라면 각 목표에 맞는 운동을 균형있게 섞어주세요.
3. 진행 분석에서 "레벨업 권장" 표시된 운동은 더 어렵거나 무거운 버전으로 대체하거나 weight_kg에 권장 무게를 반영해주세요.
4. 진행 분석에서 "현행 유지" 표시된 운동은 동일하거나 유사한 운동을 유지해주세요.
5. weight_kg 필드에는 반드시 숫자만 입력하세요. 맨몸 운동이면 0을 입력하세요. 사용자 체중({user['weight_kg']}kg)을 기준으로 직접 계산한 구체적인 kg 값을 넣어주세요. (예: 체중의 60%라면 {round(user['weight_kg'] * 0.6, 1)} 입력)
6. 반드시 아래 JSON 형식으로만 응답하세요. 설명 텍스트 없이 JSON만 출력하세요.

{{
  "exercises": [
    {{
      "name": "운동 이름",
      "category": "부위 (예: 가슴, 등, 하체, 어깨, 팔, 복근, 유산소)",
      "sets": 3,
      "reps": 12,
      "weight_kg": 40.0,
      "tip": "자세 또는 주의사항 한 줄"
    }}
  ],
  "advice": "오늘 운동 전체에 대한 맞춤 조언 2~3문장"
}}"""

def get_recent_exercises(user_id: int, days: int = 7) -> list[str]:
    """최근 N일 내 완료한 운동 이름 목록을 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name FROM workout_logs
        WHERE user_id = %s
          AND logged_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY exercise_name
        ORDER BY MAX(logged_at) DESC
        LIMIT 10
    """, (user_id, days))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r["exercise_name"] for r in rows]

def save_routine(user_id: int, exercises_json: str, ai_advice: str) -> int:
    """추천 루틴을 DB에 저장하고 routine_id를 반환합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO routines (user_id, routine_date, exercises_json, ai_advice)
        VALUES (%s, %s, %s, %s)
    """, (user_id, date.today().isoformat(), exercises_json, ai_advice))
    conn.commit()
    routine_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return routine_id

def get_today_routine(user_id: int) -> Optional[dict]:
    """오늘 이미 생성된 루틴이 있으면 반환합니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM routines
        WHERE user_id = %s AND routine_date = %s
        ORDER BY id DESC LIMIT 1
    """, (user_id, date.today().isoformat()))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def recommend_routine(user: dict) -> dict:
    """AI에게 루틴을 요청하고, 결과를 DB에 저장한 뒤 딕셔너리로 반환합니다."""

    # 오늘 루틴이 이미 있으면 재사용
    existing = get_today_routine(user["id"])
    if existing:
        console.print("[dim]오늘 루틴이 이미 있습니다. 기존 루틴을 불러옵니다.[/dim]")
        return {
            "routine_id": existing["id"],
            "exercises": json.loads(existing["exercises_json"]),
            "advice": existing["ai_advice"],
        }

    # 최근 운동 이력 조회 → 진행 분석 텍스트 생성
    past = get_recent_exercises(user["id"])
    progression_context = build_progression_context(user["id"], past)

    # 헬스장 기구 RAG: 벡터 DB에서 사용자 헬스장 정보 검색
    gym_context = retrieve_gym_context(user["id"])
    if gym_context:
        console.print("[dim]헬스장 기구 정보를 불러왔습니다. 해당 환경에 맞는 루틴을 생성합니다.[/dim]")

    prompt = _build_prompt(user, progression_context, gym_context)

    console.print("[dim]AI가 루틴을 생성 중입니다...[/dim]")

    response = client.chat.completions.create(
        model="gpt-40",      
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,           # 창의성 수준 (0~1, 높을수록 다양한 결과)
        response_format={"type": "json_object"},  # JSON만 반환하도록 강제
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    exercises = data.get("exercises", [])
    advice = data.get("advice", "")

    # DB 저장
    routine_id = save_routine(user["id"], json.dumps(exercises, ensure_ascii=False), advice)

    return {"routine_id": routine_id, "exercises": exercises, "advice": advice}

def print_routine(result: dict):
    """추천 루틴을 보기 좋게 출력합니다."""
    exercises = result["exercises"]
    advice    = result["advice"]

    # 운동 목록 테이블
    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=True)
    table.add_column("운동명",    style="bold white", min_width=16)
    table.add_column("부위",      style="cyan",       width=8)
    table.add_column("세트",      style="green",      width=6,  justify="right")
    table.add_column("횟수",      style="green",      width=6,  justify="right")
    table.add_column("무게(kg)",  style="yellow",     width=9,  justify="right")
    table.add_column("팁",        style="dim",        min_width=20)

    for ex in exercises:
        weight = ex.get("weight_kg", 0)
        weight_str = "맨몸" if weight == 0 else f"{weight}kg"
        table.add_row(
            ex.get("name", ""),
            ex.get("category", ""),
            str(ex.get("sets", "-")),
            str(ex.get("reps", "-")),
            weight_str,
            ex.get("tip", "-"),
        )

    console.print(Panel(table, title="[bold cyan]오늘의 운동 루틴[/bold cyan]", border_style="cyan"))
    console.print(Panel(f"[white]{advice}[/white]", title="[bold yellow]AI 조언[/bold yellow]", border_style="yellow"))
