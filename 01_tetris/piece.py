# piece.py — 테트로미노 데이터 + 회전 로직 (pygame 불필요)

import random
from constants import PIECES, PIECE_NAMES


class Piece:
    """
    단일 테트로미노의 상태를 담는다.
    회전은 PIECES[name]["shapes"] 배열의 인덱스 전환으로 구현 (SRS).
    """

    def __init__(self, name: str | None = None):
        self.name      = name if name else random.choice(PIECE_NAMES)
        self.data      = PIECES[self.name]
        self.color     = self.data["color"]
        self.rot_index = 0          # 현재 회전 상태 (0~3)
        self.x         = 3          # 보드 컬럼 기준 위치
        self.y         = 0          # 보드 행 기준 위치

    # ── 현재 회전 상태의 2D 행렬 반환 ──────────────────────
    @property
    def shape(self) -> list[list[int]]:
        return self.data["shapes"][self.rot_index]

    # ── 회전된 shape 미리 계산 (실제 적용 전 검증용) ───────
    def rotated(self, direction: int = 1) -> list[list[int]]:
        """direction: 1=시계방향, -1=반시계방향"""
        idx = (self.rot_index + direction) % 4
        return self.data["shapes"][idx]

    def rotate(self, direction: int = 1):
        self.rot_index = (self.rot_index + direction) % 4

    # ── 피스가 차지하는 (col, row) 셀 목록 ─────────────────
    def cells(self, shape=None, ox=None, oy=None) -> list[tuple[int, int]]:
        """shape/ox/oy 를 지정하면 가상 위치 계산에 사용"""
        s  = shape if shape is not None else self.shape
        cx = ox    if ox    is not None else self.x
        cy = oy    if oy    is not None else self.y
        return [
            (cx + c, cy + r)
            for r, row in enumerate(s)
            for c, val in enumerate(row)
            if val
        ]

    def copy(self) -> "Piece":
        p = Piece(self.name)
        p.rot_index = self.rot_index
        p.x = self.x
        p.y = self.y
        return p
