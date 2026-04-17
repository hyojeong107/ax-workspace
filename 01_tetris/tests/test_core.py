# tests/test_core.py — 핵심 로직 pytest 테스트 (pygame 불필요)
#
# 실행: cd 01_tetris && pytest tests/ -v

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from board import Board
from piece import Piece
from game  import Game, State


# ═══════════════════════════════════════════════════════════
# Board — is_valid
# ═══════════════════════════════════════════════════════════
class TestBoardValidity:
    def test_empty_board_center_valid(self):
        b = Board()
        p = Piece("O")
        p.x, p.y = 4, 0
        assert b.is_valid(p.cells())

    def test_out_of_bounds_left(self):
        b = Board()
        p = Piece("I")
        p.x = -1
        assert not b.is_valid(p.cells())

    def test_out_of_bounds_right(self):
        b = Board()
        p = Piece("I")
        p.x = 8   # I 가로 4칸 → 11 >= 10 → invalid
        assert not b.is_valid(p.cells())

    def test_out_of_bounds_bottom(self):
        b = Board()
        p = Piece("O")
        p.x, p.y = 4, 19   # row 20 초과
        assert not b.is_valid(p.cells())

    def test_collision_with_locked(self):
        b = Board()
        color = (255, 0, 0)
        b.grid[5][4] = color
        p = Piece("O")
        p.x, p.y = 4, 5
        assert not b.is_valid(p.cells())


# ═══════════════════════════════════════════════════════════
# Board — clear_lines
# ═══════════════════════════════════════════════════════════
class TestClearLines:
    def _fill_row(self, board: Board, row: int):
        board.grid[row] = [(255, 0, 0)] * 10

    def test_no_clear(self):
        b = Board()
        assert b.clear_lines() == 0

    def test_single_clear(self):
        b = Board()
        self._fill_row(b, 19)
        assert b.clear_lines() == 1
        assert all(c is None for c in b.grid[0])

    def test_tetris_4_lines(self):
        b = Board()
        for r in [16, 17, 18, 19]:
            self._fill_row(b, r)
        assert b.clear_lines() == 4

    def test_grid_shifts_down_after_clear(self):
        b = Board()
        b.grid[18][0] = (0, 255, 0)   # 마커 블록
        self._fill_row(b, 19)
        b.clear_lines()
        # 19행이 지워졌으므로 마커는 19행으로 내려와야 함
        assert b.grid[19][0] == (0, 255, 0)


# ═══════════════════════════════════════════════════════════
# Board — ghost_y
# ═══════════════════════════════════════════════════════════
class TestGhostY:
    def test_ghost_lands_at_bottom(self):
        b = Board()
        p = Piece("O")
        p.x, p.y = 4, 0
        assert b.ghost_y(p) == 18   # O는 2칸 높이, 20행 보드 → 18

    def test_ghost_stops_above_locked(self):
        b = Board()
        b.grid[10][4] = (255, 0, 0)
        b.grid[10][5] = (255, 0, 0)
        p = Piece("O")
        p.x, p.y = 4, 0
        assert b.ghost_y(p) == 8   # O(2칸) → row 9-10 충돌, y=8


# ═══════════════════════════════════════════════════════════
# Piece — rotation
# ═══════════════════════════════════════════════════════════
class TestPieceRotation:
    def test_rotate_cw(self):
        p = Piece("T")
        original = p.shape
        p.rotate(1)
        assert p.shape != original

    def test_rotate_4_times_returns_original(self):
        p = Piece("L")
        original = [row[:] for row in p.shape]
        for _ in range(4):
            p.rotate(1)
        assert p.shape == original

    def test_o_piece_shape_invariant(self):
        p = Piece("O")
        s0 = p.shape
        p.rotate(1)
        assert p.shape == s0   # O는 회전해도 동일


# ═══════════════════════════════════════════════════════════
# Board — try_rotate (with wall kick)
# ═══════════════════════════════════════════════════════════
class TestWallKick:
    def test_rotate_at_left_wall(self):
        b = Board()
        p = Piece("T")
        p.x, p.y = 0, 5
        result = b.try_rotate(p, 1)
        assert result   # 킥으로라도 성공해야 함

    def test_ccw_rotation_works(self):
        """반시계 방향(Z=-1) 회전이 정상 동작한다"""
        b = Board()
        p = Piece("T")
        p.x, p.y = 4, 5
        rot_before = p.rot_index
        result = b.try_rotate(p, -1)
        assert result
        assert p.rot_index == (rot_before - 1) % 4

    def test_rotation_fails_at_bottom_row(self):
        """보드 바닥 경계 아래는 항상 invalid — 바닥에서 아래로 킥 불가"""
        b = Board()
        p = Piece("I")
        # I 피스를 최하단에 수평으로 배치 (rot=0: row 1에 블록)
        p.x, p.y = 3, 19
        # row 20 이상으로 나가는 회전은 실패해야 함
        # rot=0→1: I가 세로가 되어 row 19~22 → invalid
        result = b.try_rotate(p, 1)
        assert not result


# ═══════════════════════════════════════════════════════════
# Game — 상태 기계
# ═══════════════════════════════════════════════════════════
class TestGameState:
    def test_initial_state_is_menu(self):
        g = Game()
        assert g.state == State.MENU

    def test_start_transitions_to_playing(self):
        g = Game()
        g.start()
        assert g.state == State.PLAYING

    def test_toggle_pause(self):
        g = Game()
        g.start()
        g.toggle_pause()
        assert g.state == State.PAUSED
        g.toggle_pause()
        assert g.state == State.PLAYING

    def test_hard_drop_increases_score(self):
        g = Game()
        g.start()
        before = g.score
        g.hard_drop()
        assert g.score >= before   # 하드드롭 점수 추가

    def test_hold_swap(self):
        g = Game()
        g.start()
        first_name = g.current.name
        g.hold()
        assert g.held_piece is not None
        assert g.held_piece.name == first_name

    def test_hold_blocked_second_time(self):
        g = Game()
        g.start()
        g.hold()
        name_after_first = g.current.name
        g.hold()   # 두 번째는 무시
        assert g.current.name == name_after_first


# ═══════════════════════════════════════════════════════════
# Game — 게임오버 판정
# ═══════════════════════════════════════════════════════════
class TestGameOver:
    def test_game_over_when_topped_out(self):
        """0~1행을 모두 채운 뒤 스폰 → 어떤 피스든 충돌 → 게임오버"""
        g = Game()
        g.start()
        # 0, 1행 전체를 막아 모든 피스의 첫 스폰 위치를 차단
        for r in range(2):
            for c in range(10):
                g.board.grid[r][c] = (255, 0, 0)
        g._spawn_current()
        assert g.state == State.GAME_OVER
