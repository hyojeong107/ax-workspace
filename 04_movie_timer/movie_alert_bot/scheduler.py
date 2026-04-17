"""
scheduler.py
APScheduler 기반 상영 종료 임박 알림 스케줄 관리 모듈.

매일 오전 9시에 watchlist를 순회하여 D-7, D-3, D-1 조건을 체크하고
notifier를 호출합니다.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# APScheduler 자체 로그는 WARNING 이상만 출력 (INFO 레벨 노이즈 억제)
logging.getLogger("apscheduler").setLevel(logging.WARNING)


class AlertScheduler:
    def __init__(self, watchlist_mgr, config_mgr):
        self.watchlist_mgr = watchlist_mgr
        self.config_mgr = config_mgr
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self._register_daily_job()

    # ── 스케줄 등록 ───────────────────────────────────────────────────────────

    def _register_daily_job(self) -> None:
        """매일 오전 9시 알림 체크 작업을 등록합니다."""
        self.scheduler.add_job(
            func=self.check_and_notify,
            trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
            id="daily_alert_check",
            name="상영 종료 임박 일일 체크",
            replace_existing=True,
        )

    # ── 스케줄러 생명주기 ─────────────────────────────────────────────────────

    def start(self) -> None:
        """백그라운드 스케줄러를 시작합니다."""
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        """스케줄러를 안전하게 종료합니다."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    # ── 알림 체크 ─────────────────────────────────────────────────────────────

    def check_and_notify(self) -> list[dict]:
        """
        watchlist를 순회하여 상영 종료 임박 영화에 대해 알림을 출력합니다.
        D-7, D-3, D-1 조건에 해당하는 영화 목록을 반환합니다.
        """
        from notifier import print_alert, print_no_alerts

        expiring = self.watchlist_mgr.get_expiring_movies()

        if not expiring:
            print_no_alerts()
            return []

        for movie in expiring:
            print_alert(movie["name"], movie["days_left"], self.config_mgr)

        return expiring

    def run_check_now(self) -> list[dict]:
        """수동 즉시 알림 체크를 실행합니다 (CLI 명령 대응용)."""
        return self.check_and_notify()
