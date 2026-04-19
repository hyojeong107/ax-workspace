# 사용자 프로필 입력 모듈
# 처음 앱을 실행할 때 건강 정보와 목표를 입력받아 DB에 저장합니다

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich import box
from db.user_repo import save_user, get_all_users, get_user

console = Console()

# 선택지 상수 정의
GENDER_OPTIONS = {"1": "male", "2": "female", "3": "other"}
FITNESS_OPTIONS = {"1": "beginner", "2": "intermediate", "3": "advanced"}
FITNESS_LABELS = {"beginner": "초보자", "intermediate": "중급자", "advanced": "고급자"}
GOAL_OPTIONS = {
    "1": "체중 감량",
    "2": "근육 증가",
    "3": "체력 향상",
    "4": "건강 유지",
    "5": "재활 / 부상 회복",
}

def _pick(prompt_text, options: dict) -> str:
    """번호로 선택지를 하나 고르는 헬퍼 함수입니다."""
    for key, label in options.items():
        console.print(f"  [cyan]{key}[/cyan]. {label}")
    while True:
        choice = Prompt.ask(prompt_text)
        if choice in options:
            return options[choice]
        console.print("[red]올바른 번호를 입력해주세요.[/red]")

def _pick_multi(prompt_text, options: dict) -> str:
    """번호를 쉼표로 구분해 여러 개 선택하는 헬퍼 함수입니다.
    예: '1,3' 입력 시 '체중 감량, 체력 향상' 반환
    """
    for key, label in options.items():
        console.print(f"  [cyan]{key}[/cyan]. {label}")
    console.print("  [dim](여러 개 선택 시 쉼표로 구분 — 예: 1,3)[/dim]")
    while True:
        raw = Prompt.ask(prompt_text)
        # 입력값을 쉼표로 분리하고 공백 제거
        keys = [k.strip() for k in raw.split(",")]
        # 중복 제거, 유효한 번호만 필터링
        valid = list(dict.fromkeys(k for k in keys if k in options))
        if valid:
            return ", ".join(options[k] for k in valid)
        console.print("[red]올바른 번호를 하나 이상 입력해주세요.[/red]")

def input_user_profile() -> int:
    """사용자 정보를 입력받고 DB에 저장한 뒤 user_id를 반환합니다."""
    console.print(Panel(
        "[bold cyan]처음 오셨군요! 맞춤 운동 루틴을 위해 정보를 입력해주세요.[/bold cyan]",
        border_style="cyan"
    ))

    # 이름
    name = Prompt.ask("\n[bold]이름[/bold]")

    # 나이
    age = IntPrompt.ask("[bold]나이[/bold] (숫자만)")

    # 성별
    console.print("\n[bold]성별[/bold]")
    gender = _pick("번호 선택", GENDER_OPTIONS)

    # 키 / 몸무게
    height_cm = FloatPrompt.ask("\n[bold]키[/bold] (cm, 예: 172.5)")
    weight_kg = FloatPrompt.ask("[bold]몸무게[/bold] (kg, 예: 68.0)")

    # 체력 수준
    console.print("\n[bold]현재 체력 수준[/bold]")
    fitness_level = _pick("번호 선택", FITNESS_OPTIONS)

    # 목표 (복수 선택 가능)
    console.print("\n[bold]운동 목표[/bold]")
    goal = _pick_multi("번호 선택", GOAL_OPTIONS)

    # 건강 주의사항 (선택 입력)
    console.print("\n[bold]건강 주의사항[/bold] [dim](부상 이력, 못 하는 운동 등 — 없으면 Enter)[/dim]")
    health_notes = Prompt.ask("입력", default="없음")

    # 입력 내용 요약 출력
    _print_summary(name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes)

    # 저장 확인
    if not Confirm.ask("\n위 정보로 저장할까요?", default=True):
        console.print("[yellow]입력을 취소했습니다.[/yellow]")
        return None

    user_id = save_user(name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes)
    console.print(f"\n[bold green]✓ 프로필이 저장되었습니다! (ID: {user_id})[/bold green]")
    return user_id

def _print_summary(name, age, gender, height_cm, weight_kg, fitness_level, goal, health_notes):
    """입력한 정보를 표 형태로 보여줍니다."""
    gender_label = {"male": "남성", "female": "여성", "other": "기타"}.get(gender, gender)

    table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0, 1))
    table.add_column("항목", style="dim", width=14)
    table.add_column("내용", style="bold white")

    table.add_row("이름",       name)
    table.add_row("나이",       f"{age}세")
    table.add_row("성별",       gender_label)
    table.add_row("키 / 몸무게", f"{height_cm}cm  /  {weight_kg}kg")
    table.add_row("체력 수준",   FITNESS_LABELS.get(fitness_level, fitness_level))
    table.add_row("목표",       goal)
    table.add_row("주의사항",   health_notes)

    console.print("\n")
    console.print(Panel(table, title="[bold cyan]입력 정보 확인[/bold cyan]", border_style="cyan"))

def select_or_create_user() -> int:
    """기존 사용자가 있으면 선택, 없으면 새로 생성하는 흐름을 처리합니다."""
    users = get_all_users()

    if not users:
        # 저장된 사용자가 없으면 바로 신규 입력
        return input_user_profile()

    # 기존 사용자 목록 출력
    console.print(Panel("[bold]기존 프로필을 선택하거나 새로 만드세요.[/bold]", border_style="cyan"))

    table = Table(box=box.SIMPLE, border_style="dim")
    table.add_column("번호", style="cyan", width=6)
    table.add_column("이름", style="bold")
    table.add_column("체력 수준")
    table.add_column("목표")

    for i, u in enumerate(users, start=1):
        table.add_row(
            str(i),
            u["name"],
            FITNESS_LABELS.get(u["fitness_level"], u["fitness_level"]),
            u["goal"],
        )
    table.add_row("[green]N[/green]", "[green]새 프로필 만들기[/green]", "", "")
    console.print(table)

    # 선택 입력
    keys = [str(i) for i in range(1, len(users) + 1)] + ["N", "n"]
    while True:
        choice = Prompt.ask("번호 또는 N 입력")
        if choice in ("N", "n"):
            return input_user_profile()
        if choice.isdigit() and 1 <= int(choice) <= len(users):
            user_id = users[int(choice) - 1]["id"]
            user = get_user(user_id)
            console.print(f"\n[green]✓ {user['name']}님, 반갑습니다![/green]")
            return user_id
        console.print("[red]올바른 번호를 입력해주세요.[/red]")
