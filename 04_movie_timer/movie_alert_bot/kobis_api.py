"""
kobis_api.py
KOBIS(영화진흥위원회) 오픈API 연동 모듈

주요 엔드포인트:
  - 영화 목록 검색 : /movie/searchMovieList.json
  - 영화 상세 정보 : /movie/searchMovieInfo.json
  - 일별 박스오피스 : /boxoffice/searchDailyBoxOfficeList.json

KOBIS API 키 발급: https://www.kobis.or.kr/kobisopenapi/homepg/apiservice/searchServiceInfo.do
"""

import math
import requests
from datetime import datetime, timedelta
from typing import Optional

KOBIS_BASE_URL = "http://www.kobis.or.kr/kobisopenapi/webservice/rest"
DEFAULT_SCREENING_WEEKS = 4  # 박스오피스 데이터 없을 때 오늘 기준 fallback 주수


class KobisAPI:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "KOBIS API 키가 설정되지 않았습니다. "
                ".env 파일에 KOBIS_API_KEY를 입력해 주세요."
            )
        self.api_key = api_key

    # ── 날짜 유틸리티 ──────────────────────────────────────────────────────────

    def format_date(self, date_str: str) -> str:
        """KOBIS 반환 형식(YYYYMMDD)을 YYYY-MM-DD로 변환합니다."""
        s = date_str.strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}"
        return s  # 이미 다른 형식이거나 빈 문자열이면 그대로 반환

    def estimate_end_date(self, movie_name: str) -> str:
        """
        최근 5일치 박스오피스 스크린 수 감소율로 예상 상영 종료일을 계산합니다.

        [알고리즘]
        1. 최근 5일치 일별 박스오피스에서 스크린 수 수집
        2. 기하평균 일간 감소율 계산
        3. 스크린 수가 10개 이하로 떨어지는 날 = 예상 종료일
        4. 데이터 부족(1개) 또는 감소 추세 없으면 스크린 수 기반 고정값 사용
        5. 박스오피스에 없는 영화 → 오늘 기준 DEFAULT_SCREENING_WEEKS 후
        """
        today = datetime.now()
        SCREEN_THRESHOLD = 10

        # 최근 5일치 스크린 수 수집 (screen_data[0] = 어제, [-1] = 5일 전)
        screen_data = []
        for days_ago in range(1, 6):
            target = (today - timedelta(days=days_ago)).strftime("%Y%m%d")
            entry = next(
                (e for e in self.get_daily_box_office(target)
                 if movie_name in e.get("movieNm", "")),
                None,
            )
            if entry:
                screen_data.append(int(entry.get("scrnCnt", 0)))

        # 박스오피스에 없는 영화 → fallback
        if not screen_data:
            return (today + timedelta(weeks=DEFAULT_SCREENING_WEEKS)).strftime("%Y-%m-%d")

        current = screen_data[0]  # 가장 최근(어제) 스크린 수

        # 이미 종료 임박
        if current <= SCREEN_THRESHOLD:
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")

        # 데이터 1개이거나 감소 추세 없으면 스크린 수 기반 고정값
        if len(screen_data) < 2 or current >= screen_data[-1]:
            if current >= 1000:
                weeks = 10
            elif current >= 500:
                weeks = 8
            elif current >= 200:
                weeks = 6
            elif current >= 50:
                weeks = 4
            else:
                weeks = 3
            return (today + timedelta(weeks=weeks)).strftime("%Y-%m-%d")

        # 기하평균 일간 감소율
        n_days = len(screen_data) - 1
        daily_rate = (current / screen_data[-1]) ** (1 / n_days)

        # 감소율이 없거나 역전되면 fallback
        if daily_rate >= 1:
            return (today + timedelta(weeks=DEFAULT_SCREENING_WEEKS)).strftime("%Y-%m-%d")

        # 스크린 수가 threshold 이하로 떨어지는 날 계산
        days_until_end = math.log(SCREEN_THRESHOLD / current) / math.log(daily_rate)
        days_until_end = max(7, int(days_until_end))  # 최소 1주

        return (today + timedelta(days=days_until_end)).strftime("%Y-%m-%d")

    # ── API 호출 ───────────────────────────────────────────────────────────────

    def _get(self, endpoint: str, params: dict) -> dict:
        """공통 GET 요청 처리."""
        url = f"{KOBIS_BASE_URL}/{endpoint}"
        params["key"] = self.api_key
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "KOBIS API 서버에 연결할 수 없습니다. 인터넷 연결 상태를 확인해 주세요."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError(
                "KOBIS API 요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
            )
        except requests.exceptions.HTTPError as exc:
            raise RuntimeError(f"KOBIS API 오류가 발생했습니다: {exc}")

    def search_movies(self, movie_name: str, limit: int = 5) -> list[dict]:
        """
        영화명으로 영화 목록을 검색합니다.
        최근 3개월 개봉작을 우선 검색하고, 결과가 없으면 전체 기간으로 재검색합니다.

        반환 필드 예시:
          movieCd   : 영화 코드 (상세 조회 키)
          movieNm   : 영화명
          openDt    : 개봉일 (YYYYMMDD)
          genreAlt  : 장르
          nationAlt : 제작국가
        """
        today = datetime.now()
        three_months_ago = today - timedelta(days=90)

        # 1차: 최근 3개월 개봉작 검색 (재개봉 포함)
        data = self._get(
            "movie/searchMovieList.json",
            {
                "movieNm": movie_name,
                "itemPerPage": limit,
                "openStartDt": three_months_ago.strftime("%Y%m%d"),
                "openEndDt": today.strftime("%Y%m%d"),
            },
        )
        results = data.get("movieListResult", {}).get("movieList", [])

        # 2차: 결과 없으면 전체 기간으로 fallback
        if not results:
            data = self._get(
                "movie/searchMovieList.json",
                {"movieNm": movie_name, "itemPerPage": limit},
            )
            results = data.get("movieListResult", {}).get("movieList", [])

        return results

    def get_movie_detail(self, movie_code: str) -> dict:
        """
        영화 코드로 상세 정보를 조회합니다.

        반환 필드 예시:
          movieNm   : 영화명
          openDt    : 개봉일
          showTm    : 상영시간(분)
          genres    : 장르 목록
          directors : 감독 목록
          actors    : 배우 목록
          companys  : 배급사 목록
        """
        data = self._get(
            "movie/searchMovieInfo.json",
            {"movieCd": movie_code},
        )
        return data.get("movieInfoResult", {}).get("movieInfo", {})

    def get_daily_box_office(self, target_date: Optional[str] = None) -> list[dict]:
        """
        일별 박스오피스를 조회합니다.
        target_date 미입력 시 전일 데이터를 반환합니다. (형식: YYYYMMDD)
        """
        if not target_date:
            yesterday = datetime.now() - timedelta(days=1)
            target_date = yesterday.strftime("%Y%m%d")
        try:
            data = self._get(
                "boxoffice/searchDailyBoxOfficeList.json",
                {"targetDt": target_date},
            )
            return data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
        except Exception:
            return []

    def is_currently_screening(self, movie_name: str) -> bool:
        """영화가 현재 일별 박스오피스에 포함되어 있는지 확인합니다."""
        for entry in self.get_daily_box_office():
            if movie_name in entry.get("movieNm", ""):
                return True
        return False
