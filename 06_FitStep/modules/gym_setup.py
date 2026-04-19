# 헬스장 기구 등록 모듈
# 사용자가 다니는 헬스장의 기구·시설 정보를 입력받아 JSON 파일 + 벡터 DB에 저장합니다

import os
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich import box
from rag.gym_rag import save_gym_to_vector_db, has_gym_data

console = Console()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _gym_file_path(user_id: int) -> str:
    return os.path.join(DATA_DIR, f"gym_{user_id}.json")


def get_gym_profile(user_id: int) -> Optional[dict]:
    """저장된 헬스장 JSON 프로필을 반환합니다. 없으면 None."""
    path = _gym_file_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_gym_json(user_id: int, data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_gym_file_path(user_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def show_gym_profile(user_id: int):
    """등록된 헬스장 기구 목록을 출력합니다."""
    profile = get_gym_profile(user_id)
    if not profile:
        console.print("[yellow]등록된 헬스장 정보가 없습니다.[/yellow]")
        return

    table = Table(box=box.SIMPLE_HEAD, border_style="dim", show_lines=False)
    table.add_column("기구명",      style="bold white", min_width=18)
    table.add_column("수량",        style="cyan",       width=6,  justify="right")
    table.add_column("무게 범위",   style="yellow",     min_width=14)
    table.add_column("비고",        style="dim",        min_width=16)

    for eq in profile["equipment"]:
        table.add_row(
            eq["name"],
            str(eq.get("quantity", 1)),
            eq.get("weight_range", "-"),
            eq.get("notes", "-"),
        )

    notes_line = f"\n[dim]특이사항: {profile['notes']}[/dim]" if profile.get("notes") else ""
    console.print(Panel(
        table,
        title=f"[bold cyan]{profile['gym_name']} 기구 목록[/bold cyan]",
        border_style="cyan",
        subtitle=notes_line,
    ))


def setup_gym(user_id: int) -> dict:
    """CLI로 헬스장 기구 정보를 입력받아 저장하고 벡터 DB에 임베딩합니다."""
    is_update = has_gym_data(user_id)
    action = "수정" if is_update else "등록"

    console.print(Panel(
        f"[bold cyan]헬스장 기구 정보 {action}[/bold cyan]\n"
        "[dim]다니는 헬스장의 기구·시설을 입력하면\n"
        "AI가 그 환경에 맞는 운동만 추천해줍니다.[/dim]",
        border_style="cyan",
    ))

    gym_name = Prompt.ask("헬스장 이름")

    equipment = []
    console.print(
        "\n[bold]기구를 하나씩 입력하세요. 빈 칸에서 Enter 누르면 종료됩니다.[/bold]\n"
        "[dim]예시: 바벨 스쿼트 렉 / 덤벨 / 스미스 머신 / 렛풀다운 / 러닝머신[/dim]\n"
    )

    idx = 1
    while True:
        name = Prompt.ask(f"  기구 {idx} 이름 (완료 시 Enter)", default="")
        if not name.strip():
            break

        quantity   = IntPrompt.ask("    수량", default=1)
        weight_range = Prompt.ask("    무게 범위 (예: 5~50kg, 없으면 Enter)", default="")
        notes      = Prompt.ask("    특이사항 (예: 붐빌 때 사용 어려움, 없으면 Enter)", default="")

        eq: dict = {"name": name.strip(), "quantity": quantity}
        if weight_range:
            eq["weight_range"] = weight_range
        if notes:
            eq["notes"] = notes

        equipment.append(eq)
        idx += 1

    if not equipment:
        console.print("[yellow]기구가 하나도 입력되지 않아 저장하지 않습니다.[/yellow]")
        return {}

    overall_notes = Prompt.ask(
        "\n헬스장 전체 특이사항 (예: 오후 6~8시 붐빔, 없으면 Enter)", default=""
    )

    gym_data = {
        "user_id":   user_id,
        "gym_name":  gym_name,
        "equipment": equipment,
        "notes":     overall_notes,
    }

    _save_gym_json(user_id, gym_data)

    console.print("\n[dim]벡터 DB에 임베딩 중...[/dim]")
    save_gym_to_vector_db(user_id, gym_data)

    console.print(
        f"[green]✓ '{gym_name}' 정보가 저장되었습니다. "
        f"이제 이 헬스장 환경에 맞는 루틴을 추천받을 수 있습니다.[/green]"
    )
    return gym_data
