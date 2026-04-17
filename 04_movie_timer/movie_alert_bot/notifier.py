"""
notifier.py
터미널 알림 메시지 출력 모듈.
상영 종료 임박 알림과 예매 URL을 사용자 친화적인 형식으로 출력합니다.
"""

from datetime import datetime
from config import ConfigManager, THEATER_INFO

_SEP_MAJOR = "=" * 60
_SEP_MINOR = "-" * 60


def print_alert(movie_name: str, days_left: int, config_mgr: ConfigManager) -> None:
    """
    D-N 상영 종료 임박 알림을 터미널에 출력합니다.

    Args:
        movie_name : 영화 제목
        days_left  : 상영 종료까지 남은 일수 (1, 3, 7)
        config_mgr : ConfigManager 인스턴스 (선호 극장 URL 조회용)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    print()
    print(_SEP_MAJOR)
    print(f"  [D-{days_left} 알림]  {now}")
    print(_SEP_MINOR)
    print(f"  '{movie_name}'의 상영 종료가 {days_left}일 남았습니다.")
    print()

    booking_urls = config_mgr.get_booking_urls(movie_name)

    if not booking_urls:
        print("  선호 극장이 설정되지 않아 전체 극장 링크를 제공합니다.")
        booking_urls = {
            info["name"]: info["search_url"].format(movie_name=movie_name)
            for info in THEATER_INFO.values()
        }

    print("  지금 예매하시겠습니까? 아래 링크를 복사하거나 브라우저에서 여세요.")
    print()
    for theater_name, url in booking_urls.items():
        print(f"  [{theater_name}]")
        print(f"  {url}")
        print()

    print(_SEP_MAJOR)
    print()


def print_booking_urls(movie_name: str, config_mgr: ConfigManager) -> None:
    """예매 URL만 단독으로 출력합니다."""
    booking_urls = config_mgr.get_booking_urls(movie_name)

    if not booking_urls:
        booking_urls = {
            info["name"]: info["search_url"].format(movie_name=movie_name)
            for info in THEATER_INFO.values()
        }

    print()
    print(_SEP_MINOR)
    print(f"  '{movie_name}' 예매 페이지")
    print(_SEP_MINOR)
    for theater_name, url in booking_urls.items():
        print(f"  [{theater_name}]  {url}")
    print(_SEP_MINOR)
    print()


def print_startup_message() -> None:
    """서비스 시작 배너를 출력합니다."""
    print()
    print(_SEP_MAJOR)
    print("  영화 상영 알림 서비스")
    print("  APScheduler가 활성화되었습니다. (매일 오전 9시 자동 체크)")
    print(_SEP_MAJOR)
    print()


def print_no_alerts() -> None:
    """알림 없음 안내 메시지를 출력합니다."""
    print()
    print("  현재 상영 종료 임박 알림이 없습니다.")
    print()
