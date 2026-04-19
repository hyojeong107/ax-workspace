# 대시보드 & 히스토리 모듈
# 지금까지 쌓인 운동 기록을 분석해서 성장 현황을 보여줍니다

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich import box
from db.database import get_connection
from modules.progression import get_overall_progress_summary, analyze_progression

console = Console()

# ── 공통 조회 함수 ─────────────────────────────────────────────────────────────

def _get_stats(user_id: int) -> dict:
    """전체 요약 통계를 한 번에 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 총 운동 세션 수 (루틴 완료 횟수)
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM routines WHERE user_id = %s AND is_completed = 1",
        (user_id,)
    )
    completed_routines = cursor.fetchone()["cnt"]

    # 총 기록된 운동 종목 수 (중복 포함)
    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM workout_logs WHERE user_id = %s",
        (user_id,)
    )
    total_logs = cursor.fetchone()["cnt"]

    # 운동한 날 수 (날짜 기준 중복 제거)
    cursor.execute(
        "SELECT COUNT(DISTINCT DATE(logged_at)) AS cnt FROM workout_logs WHERE user_id = %s",
        (user_id,)
    )
    active_days = cursor.fetchone()["cnt"]

    # 연속 운동일 수 계산 (오늘 기준으로 끊기지 않은 날)
    cursor.execute("""
        SELECT DISTINCT DATE(logged_at) AS d
        FROM workout_logs
        WHERE user_id = %s
        ORDER BY d DESC
    """, (user_id,))
    dates = [row["d"] for row in cursor.fetchall()]

    streak = 0
    if dates:
        from datetime import date, timedelta
        today = date.today()
        for i, d in enumerate(dates):
            if d == today - timedelta(days=i):
                streak += 1
            else:
                break

    cursor.close()
    conn.close()

    return {
        "completed_routines": completed_routines,
        "total_logs":         total_logs,
        "active_days":        active_days,
        "streak":             streak,
    }

def _get_recent_logs(user_id: int, limit: int = 20) -> list:
    """최근 운동 기록 목록을 가져옵니다."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT exercise_name, sets_done, reps_done, weight_kg, note,
               DATE(logged_at) AS log_date
        FROM workout_logs
        WHERE user_id = %s
        ORDER BY logged_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# ── 출력 함수 ──────────────────────────────────────────────────────────────────

def _print_summary_cards(stats: dict):
    """상단 요약 카드 4개를 가로로 출력합니다."""
    cards = [
        Panel(
            Text(str(stats["completed_routines"]), style="bold cyan", justify="center"),
            title="완료한 루틴",
            border_style="cyan",
            width=18,
        ),
        Panel(
            Text(str(stats["total_logs"]), style="bold green", justify="center"),
            title="총 운동 기록",
            border_style="green",
            width=18,
        ),
        Panel(
            Text(str(stats["active_days"]), style="bold yellow", justify="center"),
            title="운동한 날",
            border_style="yellow",
            width=18,
        ),
        Panel(
            Text(f"{stats['streak']}일 연속 🔥" if stats["streak"] > 0 else "0일",
                 style="bold red", justify="center"),
            title="연속 운동",
            border_style="red",
            width=18,
        ),
    ]
    console.print(Columns(cards))

def _print_recent_logs(logs: list):
    """최근 운동 기록 테이블을 출력합니다."""
    if not logs:
        console.print("[dim]아직 운동 기록이 없습니다.[/dim]")
        return

    table = Table(box=box.SIMPLE_HEAD, border_style="dim", show_lines=False)
    table.add_column("날짜",     style="dim",         width=12)
    table.add_column("운동명",   style="bold white",  min_width=16)
    table.add_column("세트",     style="cyan",        width=6,  justify="right")
    table.add_column("횟수",     style="cyan",        width=6,  justify="right")
    table.add_column("무게(kg)", style="yellow",      width=9,  justify="right")
    table.add_column("메모",     style="dim",         min_width=12)

    for log in logs:
        table.add_row(
            str(log["log_date"]),
            log["exercise_name"],
            str(log["sets_done"]),
            str(log["reps_done"]),
            str(log["weight_kg"]),
            log["note"] or "-",
        )

    console.print(Panel(table, title="[bold]최근 운동 기록[/bold]", border_style="dim"))

def _print_progression_table(user_id: int, summary: list):
    """운동별 성장 현황 테이블을 출력합니다."""
    if not summary:
        console.print("[dim]아직 분석할 기록이 없습니다.[/dim]")
        return

    table = Table(box=box.ROUNDED, border_style="cyan", show_lines=True)
    table.add_column("운동명",      style="bold white",  min_width=16)
    table.add_column("수행 횟수",   style="cyan",        width=10, justify="right")
    table.add_column("최고 무게",   style="yellow",      width=10, justify="right")
    table.add_column("최고 횟수",   style="green",       width=10, justify="right")
    table.add_column("상태",        width=14)
    table.add_column("다음 목표",   style="dim",         min_width=22)

    for row in summary:
        prog = analyze_progression(user_id, row["exercise_name"])
        if prog["ready_to_progress"]:
            status = Text("⬆ 레벨업!", style="bold green")
        else:
            status = Text("→ 유지",    style="dim yellow")

        table.add_row(
            row["exercise_name"],
            str(row["total_sessions"]),
            f"{row['max_weight']}kg",
            str(row["max_reps"]) + "회",
            status,
            prog["suggestion"],
        )

    console.print(Panel(
        table,
        title="[bold cyan]운동별 성장 현황[/bold cyan]",
        border_style="cyan"
    ))

# ── 메인 진입점 ────────────────────────────────────────────────────────────────

def show_dashboard(user_id: int, user_name: str):
    """대시보드 전체를 순서대로 출력합니다."""
    console.print(Panel(
        f"[bold cyan]{user_name}[/bold cyan]님의 운동 성장 대시보드",
        border_style="cyan"
    ))

    stats = _get_stats(user_id)

    # 1. 요약 카드
    _print_summary_cards(stats)

    if stats["total_logs"] == 0:
        console.print("\n[yellow]아직 운동 기록이 없어요. 오늘 첫 운동을 시작해보세요! 💪[/yellow]")
        return

    # 2. 운동별 성장 현황
    summary = get_overall_progress_summary(user_id)
    _print_progression_table(user_id, summary)

    # 3. 최근 기록 목록
    logs = _get_recent_logs(user_id)
    _print_recent_logs(logs)
