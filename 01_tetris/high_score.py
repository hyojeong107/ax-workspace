# high_score.py — 최고점수 파일 영속화

from pathlib import Path
from constants import HIGH_SCORE_FILE


def load() -> int:
    p = Path(HIGH_SCORE_FILE)
    if p.exists():
        try:
            return int(p.read_text().strip())
        except ValueError:
            pass
    return 0


def save(score: int):
    Path(HIGH_SCORE_FILE).write_text(str(score))
