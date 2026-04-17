"""
watchlist.py
관심 영화 등록 / 조회 / 삭제 / 종료일 업데이트를 담당합니다.
데이터는 data/watchlist.json 파일에 JSON 형식으로 저장됩니다.
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"


class WatchlistManager:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        if not WATCHLIST_FILE.exists():
            self._save({"movies": []})

    # ── 내부 I/O ──────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── 공개 메서드 ───────────────────────────────────────────────────────────

    def add_movie(
        self,
        movie_code: str,
        movie_name: str,
        open_date: str,
        end_date: str,
    ) -> bool:
        """
        관심 영화를 추가합니다.
        이미 동일한 영화 코드가 존재하면 False를 반환합니다(중복 방지).
        """
        data = self._load()
        for movie in data["movies"]:
            if movie["code"] == movie_code:
                return False

        data["movies"].append(
            {
                "code": movie_code,
                "name": movie_name,
                "open_date": open_date,
                "end_date": end_date,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        self._save(data)
        return True

    def get_all(self) -> list[dict]:
        """등록된 전체 관심 영화 목록을 반환합니다."""
        return self._load()["movies"]

    def remove_movie(self, movie_name: str) -> bool:
        """영화명으로 관심 목록에서 삭제합니다."""
        data = self._load()
        original = len(data["movies"])
        data["movies"] = [m for m in data["movies"] if m["name"] != movie_name]
        if len(data["movies"]) < original:
            self._save(data)
            return True
        return False

    def update_end_date(self, movie_name: str, end_date: str) -> bool:
        """영화의 상영 종료 예정일을 수정합니다."""
        data = self._load()
        for movie in data["movies"]:
            if movie["name"] == movie_name:
                movie["end_date"] = end_date
                self._save(data)
                return True
        return False

    def get_expiring_movies(self) -> list[dict]:
        """
        오늘 기준으로 D-7, D-3, D-1에 해당하는 영화를 반환합니다.
        반환 목록의 각 항목에는 'days_left' 키가 추가됩니다.
        """
        today = datetime.now().date()
        alert_days = {7, 3, 1}
        result = []

        for movie in self.get_all():
            end_date_str = movie.get("end_date", "")
            if not end_date_str:
                continue
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                days_left = (end_date - today).days
                if days_left in alert_days:
                    result.append({**movie, "days_left": days_left})
            except ValueError:
                continue

        return result
