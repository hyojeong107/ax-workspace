"""
main.py
영화 상영 알림 서비스 CLI 진입점.

OpenAI Chat Completions API (Function Calling) 를 활용해 자연어 대화로
watchlist 관리, 극장 설정, 알림 확인, 예매 URL 안내를 통합 제공합니다.
"""

import json
import os
import signal
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from config import ConfigManager
from kobis_api import KobisAPI
from notifier import print_startup_message
from scheduler import AlertScheduler
from watchlist import WatchlistManager

# ── 컴포넌트 초기화 ────────────────────────────────────────────────────────────

_openai_key = os.getenv("OPENAI_API_KEY", "")
_kobis_key = os.getenv("KOBIS_API_KEY", "")

client = OpenAI(api_key=_openai_key)
watchlist_mgr = WatchlistManager()
config_mgr = ConfigManager()
scheduler = AlertScheduler(watchlist_mgr, config_mgr)

# KOBIS API는 키가 없으면 None으로 설정하여 graceful 처리
try:
    kobis = KobisAPI(api_key=_kobis_key)
except ValueError:
    kobis = None

# ── 시스템 프롬프트 ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
당신은 영화 상영 알림 서비스 챗봇입니다.
사용자가 관심 영화를 등록하고, 선호 극장을 설정하며, 상영 종료 알림을 확인할 수 있도록 도와드립니다.

[응답 원칙]
- 전문적이고 정중한 어조로, 존댓말을 사용합니다.
- 과도한 감탄사나 이모지는 사용하지 않습니다.
- 오류 발생 시 기술적 용어 대신 사용자가 이해할 수 있는 언어로 안내합니다.
- 기능 실행 후 결과를 간결하게 요약하여 보고합니다.

[지원 기능]
1. 관심 영화 등록 / 조회 / 삭제: search_movie → add_to_watchlist / get_watchlist / remove_from_watchlist
2. 선호 극장 설정 (CGV, 롯데시네마, 메가박스): set_theater_preference / get_theater_preference
3. 상영 종료 임박 알림 즉시 확인: check_alerts_now
4. 예매 페이지 URL 안내: get_booking_urls
5. 상영 종료일 수정: update_end_date

[영화 등록 흐름]
사용자가 영화 등록을 요청하면:
1. search_movie 로 KOBIS 검색 결과를 확인합니다.
2. 검색 결과를 사용자에게 보여주고 확인을 받습니다.
3. add_to_watchlist 를 호출하여 등록합니다.
   - open_date 는 검색 결과의 개봉일을 사용합니다.
   - end_date 는 estimated_end_date 값을 기본값으로 사용하되, 사용자가 별도로 지정하면 해당 날짜를 사용합니다.
   - KOBIS API 키가 미설정이거나 검색 결과가 없으면 사용자에게 안내하고, 영화 코드는 'MANUAL-[영화명]', 날짜는 사용자 입력을 사용합니다.

[극장 코드]
- CGV → cgv
- 롯데시네마 → lotte
- 메가박스 → megabox

[예상 상영 종료일 계산 방식]
estimated_end_date 는 다음 알고리즘으로 산출됩니다:
1. 최근 5일치 일별 박스오피스에서 해당 영화의 스크린 수를 수집합니다.
2. 기하평균으로 일간 스크린 수 감소율을 계산합니다.
3. 스크린 수가 10개 이하로 떨어지는 날을 예상 종료일로 추정합니다.
4. 데이터가 1개뿐이거나 감소 추세가 없으면 현재 스크린 수 규모로 고정값을 사용합니다.
   (1000개↑ → 10주 / 500개↑ → 8주 / 200개↑ → 6주 / 50개↑ → 4주 / 50개↓ → 3주)
5. 박스오피스에 없는 영화(소규모·재개봉 등)는 오늘 기준 4주 후를 기본값으로 사용합니다.
이 값은 추정치이며 실제 상영 종료일과 다를 수 있습니다. 사용자가 직접 수정할 수 있습니다.
"""

# ── Tool 정의 ──────────────────────────────────────────────────────────────────

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_movie",
            "description": "KOBIS API를 통해 영화 제목으로 영화를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_name": {"type": "string", "description": "검색할 영화 제목"},
                },
                "required": ["movie_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_watchlist",
            "description": "영화를 관심 목록에 추가합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_code": {"type": "string", "description": "KOBIS 영화 코드"},
                    "movie_name": {"type": "string", "description": "영화 제목"},
                    "open_date": {"type": "string", "description": "개봉일 (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "예상 상영 종료일 (YYYY-MM-DD)"},
                },
                "required": ["movie_code", "movie_name", "open_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_watchlist",
            "description": "현재 등록된 관심 영화 목록을 조회합니다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_watchlist",
            "description": "관심 목록에서 영화를 삭제합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_name": {"type": "string", "description": "삭제할 영화 제목"},
                },
                "required": ["movie_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_theater_preference",
            "description": "선호 극장을 설정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theaters": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["cgv", "lotte", "megabox"],
                        },
                        "description": "선호 극장 코드 목록 (cgv / lotte / megabox)",
                    },
                },
                "required": ["theaters"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_theater_preference",
            "description": "현재 설정된 선호 극장을 조회합니다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking_urls",
            "description": "영화의 선호 극장 예매 페이지 URL을 제공합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_name": {"type": "string", "description": "예매할 영화 제목"},
                },
                "required": ["movie_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_alerts_now",
            "description": "현재 상영 종료 임박 알림을 즉시 확인합니다.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_end_date",
            "description": "관심 목록에 등록된 영화의 상영 종료 예정일을 수정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_name": {"type": "string", "description": "수정할 영화 제목"},
                    "end_date": {"type": "string", "description": "새 상영 종료 예정일 (YYYY-MM-DD)"},
                },
                "required": ["movie_name", "end_date"],
            },
        },
    },
]

# ── Tool 실행 ──────────────────────────────────────────────────────────────────

def _execute_tool(name: str, args: dict) -> str:
    """Tool 이름과 인자를 받아 실행하고 JSON 문자열을 반환합니다."""

    def ok(msg: str, **extra) -> str:
        return json.dumps({"result": msg, **extra}, ensure_ascii=False)

    def err(msg: str) -> str:
        return json.dumps({"result": msg}, ensure_ascii=False)

    try:
        # ── 영화 검색 ──────────────────────────────────────────────────────────
        if name == "search_movie":
            if kobis is None:
                return err(
                    "KOBIS API 키가 설정되지 않아 영화 검색을 이용할 수 없습니다. "
                    ".env 파일에 KOBIS_API_KEY를 입력해 주세요."
                )
            movies = kobis.search_movies(args["movie_name"])
            if not movies:
                return ok("검색 결과가 없습니다.", movies=[])
            simplified = []
            for m in movies[:5]:
                open_date = kobis.format_date(m.get("openDt", ""))
                simplified.append(
                    {
                        "code": m.get("movieCd", ""),
                        "name": m.get("movieNm", ""),
                        "open_date": open_date,
                        "estimated_end_date": kobis.estimate_end_date(m.get("movieNm", "")),
                        "genre": m.get("genreAlt", ""),
                        "nation": m.get("nationAlt", ""),
                    }
                )
            return ok("검색 성공", movies=simplified)

        # ── 관심 영화 추가 ─────────────────────────────────────────────────────
        elif name == "add_to_watchlist":
            success = watchlist_mgr.add_movie(
                args["movie_code"],
                args["movie_name"],
                args.get("open_date", ""),
                args.get("end_date", ""),
            )
            if success:
                return ok(f"'{args['movie_name']}'을(를) 관심 목록에 등록했습니다.")
            return ok(f"'{args['movie_name']}'은(는) 이미 관심 목록에 등록되어 있습니다.")

        # ── 관심 목록 조회 ─────────────────────────────────────────────────────
        elif name == "get_watchlist":
            movies = watchlist_mgr.get_all()
            if not movies:
                return ok("등록된 관심 영화가 없습니다.", movies=[])
            return ok("조회 성공", movies=movies)

        # ── 관심 영화 삭제 ─────────────────────────────────────────────────────
        elif name == "remove_from_watchlist":
            success = watchlist_mgr.remove_movie(args["movie_name"])
            if success:
                return ok(f"'{args['movie_name']}'을(를) 관심 목록에서 삭제했습니다.")
            return ok(f"'{args['movie_name']}'을(를) 관심 목록에서 찾을 수 없습니다.")

        # ── 극장 설정 ──────────────────────────────────────────────────────────
        elif name == "set_theater_preference":
            config_mgr.set_theaters(args["theaters"])
            names = config_mgr.get_theater_names()
            return ok(f"선호 극장이 설정되었습니다: {', '.join(names)}")

        elif name == "get_theater_preference":
            names = config_mgr.get_theater_names()
            if not names:
                return ok("선호 극장이 설정되지 않았습니다.", theaters=[])
            return ok("조회 성공", theaters=names)

        # ── 예매 URL ───────────────────────────────────────────────────────────
        elif name == "get_booking_urls":
            urls = config_mgr.get_booking_urls(args["movie_name"])
            return ok("조회 성공", movie=args["movie_name"], urls=urls)

        # ── 즉시 알림 체크 ─────────────────────────────────────────────────────
        elif name == "check_alerts_now":
            expiring = scheduler.run_check_now()
            if not expiring:
                return ok("현재 상영 종료 임박 알림이 없습니다.", alerts=[])
            alerts = [
                {
                    "name": m["name"],
                    "days_left": m["days_left"],
                    "end_date": m["end_date"],
                }
                for m in expiring
            ]
            return ok("알림 확인 완료", alerts=alerts)

        # ── 종료일 수정 ────────────────────────────────────────────────────────
        elif name == "update_end_date":
            success = watchlist_mgr.update_end_date(args["movie_name"], args["end_date"])
            if success:
                return ok(
                    f"'{args['movie_name']}'의 상영 종료 예정일이 "
                    f"{args['end_date']}로 변경되었습니다."
                )
            return ok(f"'{args['movie_name']}'을(를) 관심 목록에서 찾을 수 없습니다.")

        else:
            return err("알 수 없는 기능입니다.")

    except ConnectionError as exc:
        return err(str(exc))
    except TimeoutError as exc:
        return err(str(exc))
    except Exception as exc:
        return err(f"처리 중 오류가 발생했습니다: {exc}")


# ── OpenAI 대화 처리 ────────────────────────────────────────────────────────────

def _chat(history: list[dict]) -> str:
    """
    OpenAI Chat Completions API를 호출하고 Tool Call을 처리합니다.
    최종 assistant 텍스트 응답을 반환합니다.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = response.choices[0].message

    # Tool Call 루프 처리
    while msg.tool_calls:
        history.append(msg)
        tool_results = []
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result_content = _execute_tool(tc.function.name, args)
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_content,
                }
            )
        history.extend(tool_results)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message

    return msg.content or ""


# ── 메인 루프 ──────────────────────────────────────────────────────────────────

def main() -> None:
    # 환경 변수 검증
    if not _openai_key:
        print("[오류] OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")
        sys.exit(1)

    print_startup_message()
    scheduler.start()

    if kobis is None:
        print("  [주의] KOBIS_API_KEY가 설정되지 않아 영화 검색 기능이 제한됩니다.")
        print("         .env 파일에 KOBIS_API_KEY를 추가하면 KOBIS 검색이 활성화됩니다.")
        print()

    def _handle_exit(sig, frame) -> None:
        print("\n\n  서비스를 종료합니다. 이용해 주셔서 감사합니다.")
        scheduler.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_exit)

    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("  안녕하세요. 영화 상영 알림 서비스입니다. 무엇을 도와드릴까요?")
    print("  (종료하려면 Ctrl+C를 누르거나 '종료'를 입력하세요.)\n")

    while True:
        try:
            user_input = input("사용자: ").strip()
        except EOFError:
            _handle_exit(None, None)

        if not user_input:
            continue

        if user_input.lower() in ("종료", "exit", "quit", "bye"):
            _handle_exit(None, None)

        history.append({"role": "user", "content": user_input})

        try:
            reply = _chat(history)
            history.append({"role": "assistant", "content": reply})
            print(f"\n챗봇: {reply}\n")
        except Exception:
            error_reply = (
                "죄송합니다. 요청을 처리하는 중 문제가 발생했습니다. "
                "잠시 후 다시 시도해 주세요."
            )
            print(f"\n챗봇: {error_reply}\n")
            # 실패한 사용자 메시지를 히스토리에서 제거하여 맥락 오염 방지
            if history and history[-1]["role"] == "user":
                history.pop()


if __name__ == "__main__":
    main()
