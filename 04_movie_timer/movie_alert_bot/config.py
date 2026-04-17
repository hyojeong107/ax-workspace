"""
config.py
선호 극장 설정 및 예매 URL 관리 모듈.
설정은 data/config.json에 저장됩니다.
"""

import json
from pathlib import Path
from urllib.parse import quote

DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = DATA_DIR / "config.json"

# 지원 극장 정보 (코드 → 이름, 검색 URL, 예매 URL)
THEATER_INFO: dict[str, dict] = {
    "cgv": {
        "name": "CGV",
        "search_url": "https://www.cgv.co.kr/movies/?SearchKeyword={movie_name}",
        "booking_url": "https://www.cgv.co.kr/movies/",
    },
    "lotte": {
        "name": "롯데시네마",
        "search_url": "https://www.lottecinema.co.kr/NLCHS/Movie/MovieListView?searchText={movie_name}",
        "booking_url": "https://www.lottecinema.co.kr/NLCHS/Ticketing",
    },
    "megabox": {
        "name": "메가박스",
        "search_url": "https://www.megabox.co.kr/movie?searchKeyword={movie_name}",
        "booking_url": "https://www.megabox.co.kr/booking",
    },
}


class ConfigManager:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not CONFIG_FILE.exists():
            self._save({"theaters": [], "notification_days": [7, 3, 1]})

    # ── 내부 I/O ──────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 극장 설정 ─────────────────────────────────────────────────────────────

    def set_theaters(self, theaters: list[str]) -> None:
        """
        선호 극장 코드 목록을 저장합니다.
        유효하지 않은 코드는 무시됩니다. (cgv / lotte / megabox)
        """
        valid = [t.lower() for t in theaters if t.lower() in THEATER_INFO]
        data = self._load()
        data["theaters"] = valid
        self._save(data)

    def get_theaters(self) -> list[str]:
        """저장된 선호 극장 코드 목록을 반환합니다."""
        return self._load().get("theaters", [])

    def get_theater_names(self) -> list[str]:
        """선호 극장의 한글 이름 목록을 반환합니다."""
        return [
            THEATER_INFO[code]["name"]
            for code in self.get_theaters()
            if code in THEATER_INFO
        ]

    def get_booking_urls(self, movie_name: str) -> dict[str, str]:
        """전체 극장의 영화 검색 URL을 반환합니다."""
        encoded = quote(movie_name)
        return {
            THEATER_INFO[code]["name"]: THEATER_INFO[code]["search_url"].format(
                movie_name=encoded
            )
            for code in THEATER_INFO
        }

    def get_notification_days(self) -> list[int]:
        """알림을 발송하는 D-N 목록을 반환합니다."""
        return self._load().get("notification_days", [7, 3, 1])
