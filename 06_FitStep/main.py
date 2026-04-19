# FitStep - 나만의 헬스 코치 CLI 앱
# 메인 진입점: 프로그램을 실행하면 이 파일이 가장 먼저 실행됩니다

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from db.database import init_db
from db.user_repo import get_user
from modules.user_setup import select_or_create_user
from modules.recommender import recommend_routine, print_routine
from modules.workout_logger import run_workout_logging
from modules.dashboard import show_dashboard
from modules.gym_setup import setup_gym, show_gym_profile
from rag.gym_rag import has_gym_data

console = Console()

def main():
    init_db()

    # 환영 메시지
    title = Text("💪 FitStep", style="bold cyan", justify="center")
    subtitle = Text("나만의 AI 헬스 코치", style="dim white", justify="center")
    console.print(Panel(f"{title}\n{subtitle}", border_style="cyan", padding=(1, 4)))

    # 사용자 선택 또는 신규 생성
    user_id = select_or_create_user()
    if user_id is None:
        console.print("[yellow]프로그램을 종료합니다.[/yellow]")
        return

    user = dict(get_user(user_id))

    # 헬스장 정보 미등록 시 첫 실행에서 안내
    if not has_gym_data(user_id):
        console.print(
            "\n[yellow]⚠  헬스장 기구 정보가 없습니다.[/yellow]\n"
            "[dim]메뉴 4번에서 등록하면 AI가 실제 헬스장 환경에 맞는 루틴을 추천해줍니다.[/dim]"
        )

    # 오늘의 루틴을 세션 내에서 공유 (추천 후 바로 기록 가능)
    today_result = None

    # 메인 메뉴
    while True:
        console.print("\n[bold cyan]━━━ 메뉴 ━━━[/bold cyan]")
        console.print("  [cyan]1[/cyan]. 오늘의 운동 루틴 추천 받기")
        console.print("  [cyan]2[/cyan]. 운동 완료 기록하기")
        console.print("  [cyan]3[/cyan]. 성장 대시보드 보기")
        console.print("  [cyan]4[/cyan]. 헬스장 기구 등록 / 수정")
        console.print("  [cyan]q[/cyan]. 종료")

        choice = Prompt.ask("\n선택")

        if choice == "1":
            today_result = recommend_routine(user)
            print_routine(today_result)

        elif choice == "2":
            if today_result is None:
                today_result = recommend_routine(user)
                print_routine(today_result)
            run_workout_logging(user_id, today_result)

        elif choice == "3":
            show_dashboard(user_id, user["name"])

        elif choice == "4":
            show_gym_profile(user_id)
            ans = Prompt.ask("\n[dim]새로 등록 / 수정하시겠습니까?[/dim]", choices=["y", "n"], default="n")
            if ans == "y":
                setup_gym(user_id)
                # 오늘 루틴 캐시 초기화: 헬스장 변경 후 새 루틴 받을 수 있도록
                today_result = None

        elif choice in ("q", "Q"):
            console.print("[yellow]FitStep을 종료합니다. 오늘도 수고하셨습니다! 💪[/yellow]")
            break

        else:
            console.print("[red]올바른 메뉴를 선택해주세요.[/red]")

if __name__ == "__main__":
    main()
