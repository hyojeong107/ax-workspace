# 운동 완료 기록 모듈
# 오늘 루틴의 각 운동을 하나씩 확인하며 실제 수행 결과를 입력받아 저장합니다

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich import box
from db.database import get_connection

console = Console()

def save_log(user_id: int, routine_id: int, exercise_name: str,
             sets_done: int, reps_done: int, weight_kg: float, note: str):
    """운동 한 종목의 완료 기록을 DB에 저장합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workout_logs
            (user_id, routine_id, exercise_name, sets_done, reps_done, weight_kg, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, routine_id, exercise_name, sets_done, reps_done, weight_kg, note))
    conn.commit()
    cursor.close()
    conn.close()

def mark_routine_complete(routine_id: int):
    """루틴 전체를 완료 상태로 업데이트합니다."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE routines SET is_completed = 1 WHERE id = %s", (routine_id,)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_logged_exercises(routine_id: int) -> list:
    """이 루틴에서 이미 기록된 운동 이름 목록을 반환합니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT exercise_name FROM workout_logs WHERE routine_id = %s", (routine_id,)
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [r["exercise_name"] for r in rows]

def _log_single_exercise(user_id: int, routine_id: int, ex: dict):
    """운동 한 종목에 대한 실제 수행 결과를 입력받고 저장합니다."""
    console.print(Panel(
        f"[bold white]{ex['name']}[/bold white]\n"
        f"[dim]부위: {ex.get('category','-')}  |  "
        f"목표: {ex.get('sets','-')}세트 × {ex.get('reps','-')}회  |  "
        f"권장 무게: {ex.get('weight_kg', 0)}kg[/dim]\n"
        f"[yellow]팁: {ex.get('tip','')}[/yellow]",
        border_style="cyan",
        title=f"[cyan]운동 기록[/cyan]"
    ))

    # 실제 수행한 세트 수 입력
    sets_done  = IntPrompt.ask("  실제 수행한 세트 수", default=int(ex.get("sets", 3)))
    reps_done  = IntPrompt.ask("  실제 수행한 반복 수", default=int(ex.get("reps", 10)))
    weight_kg  = FloatPrompt.ask("  사용한 무게 (kg, 맨몸이면 0)", default=float(ex.get("weight_kg", 0.0)))
    note       = Prompt.ask("  메모 (없으면 Enter)", default="")

    save_log(user_id, routine_id, ex["name"], sets_done, reps_done, weight_kg, note)
    console.print(f"  [green]✓ 기록 완료![/green]\n")

def run_workout_logging(user_id: int, routine_result: dict):
    """루틴 전체를 순서대로 돌며 완료 기록을 받습니다."""
    routine_id = routine_result["routine_id"]
    exercises  = routine_result["exercises"]

    # 이미 기록된 운동은 건너뜁니다 (중간에 앱을 껐다 켜도 이어서 진행 가능)
    already_logged = set(get_logged_exercises(routine_id))

    todo = [ex for ex in exercises if ex["name"] not in already_logged]

    if not todo:
        console.print("[green]오늘 루틴이 이미 모두 완료되었습니다! 🎉[/green]")
        return

    console.print(Panel(
        f"[bold]총 {len(exercises)}개 운동 중 [cyan]{len(todo)}개[/cyan] 남았습니다.[/bold]\n"
        "[dim]각 운동이 끝날 때마다 결과를 입력해주세요.[/dim]",
        border_style="cyan"
    ))

    completed = list(already_logged)  # 이번 세션에서 완료한 운동 누적

    for ex in todo:
        # 이 운동을 건너뛸지 확인
        if not Confirm.ask(f"\n  [bold]{ex['name']}[/bold] 를 완료했나요?", default=True):
            console.print("  [dim]건너뜁니다.[/dim]")
            continue

        _log_single_exercise(user_id, routine_id, ex)
        completed.append(ex["name"])

    # 루틴의 모든 운동이 완료됐으면 routines 테이블도 완료 표시
    all_names = {ex["name"] for ex in exercises}
    if all_names <= set(completed):
        mark_routine_complete(routine_id)
        _print_completion_summary(user_id, routine_id)
    else:
        remaining = len(all_names) - len(set(completed) & all_names)
        console.print(f"\n[yellow]오늘 루틴 {remaining}개 운동이 남아있습니다. 나중에 이어서 기록할 수 있습니다.[/yellow]")

def _print_completion_summary(user_id: int, routine_id: int):
    """루틴 완료 시 오늘의 운동 요약을 출력합니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name, sets_done, reps_done, weight_kg, note
        FROM workout_logs
        WHERE routine_id = %s AND user_id = %s
        ORDER BY logged_at
    """, (routine_id, user_id))
    logs = cursor.fetchall()
    cursor.close()
    conn.close()

    table = Table(box=box.ROUNDED, border_style="green", show_lines=True)
    table.add_column("운동명",   style="bold white", min_width=16)
    table.add_column("세트",     style="cyan",  width=6)
    table.add_column("횟수",     style="cyan",  width=6)
    table.add_column("무게(kg)", style="yellow", width=9)
    table.add_column("메모",     style="dim",   min_width=14)

    for log in logs:
        table.add_row(
            log["exercise_name"],
            str(log["sets_done"]),
            str(log["reps_done"]),
            str(log["weight_kg"]),
            log["note"] or "-",
        )

    console.print("\n")
    console.print(Panel(
        table,
        title="[bold green]🎉 오늘 운동 완료! 수고하셨습니다![/bold green]",
        border_style="green"
    ))
