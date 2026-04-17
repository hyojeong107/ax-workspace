# game.py — 게임 상태 기계 (pygame 불필요)
# 상태: MENU / PLAYING / PAUSED / GAME_OVER

from enum import Enum, auto
import random

from constants import (
    COLS, FALL_SPEEDS, MAX_LEVEL, LINES_PER_LEVEL,
    SOFT_DROP_PTS, HARD_DROP_PTS, SCORE_TABLE, LOCK_DELAY,
)
from board import Board
from piece import Piece
import high_score


class State(Enum):
    MENU      = auto()
    PLAYING   = auto()
    PAUSED    = auto()
    GAME_OVER = auto()


class Game:
    def __init__(self):
        self.high_score = high_score.load()
        self._reset()

    # ── 초기화 ──────────────────────────────────────────────
    def _reset(self):
        self.board        = Board()
        self.score        = 0
        self.level        = 0
        self.lines        = 0        # 총 삭제 줄 수
        self.state        = State.MENU

        # 피스 bag: 7-bag randomizer
        self._bag: list[str] = []
        self.current      = self._next_piece()
        self.next_piece   = self._next_piece()
        self.held_piece: Piece | None = None
        self.hold_used    = False    # 한 턴에 홀드 1회 제한

        self._fall_acc    = 0        # 자동낙하 누적 ms
        self._lock_acc    = 0        # 잠금 딜레이 누적 ms
        self._on_ground   = False    # 피스가 바닥에 닿았는가

    # ── 7-bag 랜덤 생성기 ───────────────────────────────────
    def _next_piece(self) -> Piece:
        if not self._bag:
            from constants import PIECE_NAMES
            self._bag = list(PIECE_NAMES)
            random.shuffle(self._bag)
        return Piece(self._bag.pop())

    # ── 낙하 속도 (레벨 기반) ───────────────────────────────
    @property
    def fall_speed(self) -> int:
        return FALL_SPEEDS[min(self.level, MAX_LEVEL)]

    # ── 공개 API ─────────────────────────────────────────────

    def start(self):
        self._reset()
        self.state = State.PLAYING

    def toggle_pause(self):
        if self.state == State.PLAYING:
            self.state = State.PAUSED
        elif self.state == State.PAUSED:
            self.state = State.PLAYING

    # ── 이동 ────────────────────────────────────────────────
    def move(self, dx: int) -> bool:
        cells = self.current.cells(ox=self.current.x + dx)
        if self.board.is_valid(cells):
            self.current.x += dx
            self._lock_acc = 0   # 이동 시 잠금 딜레이 리셋
            return True
        return False

    # ── 회전 ────────────────────────────────────────────────
    def rotate(self, direction: int = 1):
        if self.board.try_rotate(self.current, direction):
            self._lock_acc = 0

    # ── 소프트드롭 ──────────────────────────────────────────
    def soft_drop(self) -> bool:
        if self._move_down():
            self.score += SOFT_DROP_PTS
            return True
        return False

    # ── 하드드롭 ────────────────────────────────────────────
    def hard_drop(self):
        dropped = 0
        while self._move_down():
            dropped += 1
        self.score += dropped * HARD_DROP_PTS
        self._lock_piece()

    # ── 홀드 ────────────────────────────────────────────────
    def hold(self):
        if self.hold_used:
            return

        if self.held_piece is None:
            self.held_piece = Piece(self.current.name)
            self._spawn_next()
        else:
            self.current, self.held_piece = (
                Piece(self.held_piece.name),
                Piece(self.current.name),
            )
            self._spawn_current()

        # _spawn_next()/_spawn_current() 내부에서 hold_used=False로 리셋되므로
        # 홀드 완료 후 다시 True로 설정해야 한다.
        self.hold_used = True

    # ── 매 프레임 업데이트 (dt: ms) ─────────────────────────
    def update(self, dt: int):
        if self.state != State.PLAYING:
            return

        self._fall_acc += dt

        on_ground = not self.board.is_valid(
            self.current.cells(oy=self.current.y + 1)
        )

        if on_ground:
            self._lock_acc += dt
            if self._lock_acc >= LOCK_DELAY:
                self._lock_piece()
                return
        else:
            self._lock_acc = 0

        if self._fall_acc >= self.fall_speed:
            self._fall_acc = 0
            self._move_down()

    # ── 내부 헬퍼 ───────────────────────────────────────────
    def _move_down(self) -> bool:
        cells = self.current.cells(oy=self.current.y + 1)
        if self.board.is_valid(cells):
            self.current.y += 1
            return True
        return False

    def _lock_piece(self):
        self.board.lock(self.current)
        cleared = self.board.clear_lines()
        if cleared:
            base = SCORE_TABLE.get(cleared, 800)
            self.score += base * (self.level + 1)
            self.lines += cleared
            self.level = self.lines // LINES_PER_LEVEL

        if self.score > self.high_score:
            self.high_score = self.score
            high_score.save(self.high_score)

        self._spawn_next()

    def _spawn_next(self):
        self.current    = self.next_piece
        self.next_piece = self._next_piece()
        self.hold_used  = False
        self._fall_acc  = 0
        self._lock_acc  = 0
        self._spawn_current()

    def _spawn_current(self):
        """피스를 보드 상단 중앙에 배치, 충돌이면 게임오버"""
        self.current.x = COLS // 2 - len(self.current.shape[0]) // 2
        self.current.y = 0

        if not self.board.is_valid(self.current.cells()):
            self.state = State.GAME_OVER

    # ── 읽기 전용 정보 ───────────────────────────────────────
    @property
    def ghost_y(self) -> int:
        return self.board.ghost_y(self.current)
