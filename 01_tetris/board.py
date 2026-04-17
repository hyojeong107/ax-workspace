# board.py — 보드 상태 + 충돌/잠금/줄삭제 (pygame 불필요)

from constants import COLS, ROWS
from piece import Piece


class Board:
    """
    격자(grid)는 None 또는 RGB 튜플로 채워진다.
    None = 빈 셀, (r,g,b) = 고정된 블록 색상.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.grid: list[list[tuple | None]] = [
            [None] * COLS for _ in range(ROWS)
        ]

    # ── 충돌 검사 ───────────────────────────────────────────
    def is_valid(self, cells: list[tuple[int, int]]) -> bool:
        """주어진 셀 목록이 보드 안에 있고 빈 칸인지 확인"""
        for col, row in cells:
            if col < 0 or col >= COLS:
                return False
            if row >= ROWS:
                return False
            if row >= 0 and self.grid[row][col] is not None:
                return False
        return True

    # ── 피스 잠금 ───────────────────────────────────────────
    def lock(self, piece: Piece):
        for col, row in piece.cells():
            if 0 <= row < ROWS and 0 <= col < COLS:
                self.grid[row][col] = piece.color

    # ── 줄 삭제 → 삭제된 줄 수 반환 ───────────────────────
    def clear_lines(self) -> int:
        full_rows = [r for r in range(ROWS) if all(self.grid[r])]
        for r in full_rows:
            del self.grid[r]
            self.grid.insert(0, [None] * COLS)
        return len(full_rows)

    # ── 고스트 피스 y 계산 ──────────────────────────────────
    def ghost_y(self, piece: Piece) -> int:
        drop = 0
        while True:
            test_cells = piece.cells(oy=piece.y + drop + 1)
            if not self.is_valid(test_cells):
                break
            drop += 1
        return piece.y + drop

    # ── 게임오버 판정: 0행 위에 블록이 있는가 ──────────────
    def is_topped_out(self) -> bool:
        return any(self.grid[0][c] is not None for c in range(COLS))

    # ── SRS 월킥 테이블 (간략화) ────────────────────────────
    # 표준 SRS 킥 오프셋. 키: (현재rot, 다음rot)
    WALL_KICKS = {
        (0,1): [(-1,0),(+1,0),(-1,-1),(+1,+1)],
        (1,0): [(+1,0),(-1,0),(+1,+1),(-1,-1)],
        (1,2): [(-1,0),(+1,0),(-1,+1),(+1,-1)],
        (2,1): [(+1,0),(-1,0),(+1,-1),(-1,+1)],
        (2,3): [(+1,0),(-1,0),(+1,+1),(-1,-1)],
        (3,2): [(-1,0),(+1,0),(-1,-1),(+1,+1)],
        (3,0): [(-1,0),(+1,0),(-1,+1),(+1,-1)],
        (0,3): [(+1,0),(-1,0),(+1,-1),(-1,+1)],
    }

    def try_rotate(self, piece: Piece, direction: int = 1) -> bool:
        """
        SRS 회전 시도. 성공 시 piece 상태 변경 후 True 반환.
        """
        next_rot = (piece.rot_index + direction) % 4
        next_shape = piece.data["shapes"][next_rot]

        # 기본 시도
        cells = piece.cells(shape=next_shape)
        if self.is_valid(cells):
            piece.rotate(direction)
            return True

        # 월킥 시도
        key = (piece.rot_index, next_rot)
        for dx, dy in self.WALL_KICKS.get(key, []):
            cells = piece.cells(shape=next_shape, ox=piece.x + dx, oy=piece.y + dy)
            if self.is_valid(cells):
                piece.x += dx
                piece.y += dy
                piece.rotate(direction)
                return True

        return False
