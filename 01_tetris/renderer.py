# renderer.py — 화면 렌더링 전담 (game 상태를 읽기만 함)

import pygame
from constants import (
    BLOCK_SIZE, COLS, ROWS,
    PLAY_WIDTH, PLAY_HEIGHT,
    BOARD_OFFSET_X, BOARD_OFFSET_Y,
    WINDOW_WIDTH, WINDOW_HEIGHT,
    BLACK, WHITE, GRAY, DARK_GRAY, LIGHT_GRAY,
    RED, GREEN, BLUE, YELLOW, BORDER_COLOR,
)
from game import Game, State


# ── 팔레트 ─────────────────────────────────────────────────
PANEL_BG    = (20, 20, 35)
TITLE_COLOR = (100, 200, 255)
KEY_COLOR   = (180, 180, 180)
GHOST_COLOR = (80, 80, 80)


def _block_rect(col: int, row: int) -> pygame.Rect:
    return pygame.Rect(
        BOARD_OFFSET_X + col * BLOCK_SIZE,
        BOARD_OFFSET_Y + row * BLOCK_SIZE,
        BLOCK_SIZE, BLOCK_SIZE,
    )


def _draw_block(surf: pygame.Surface, color: tuple, col: int, row: int,
                alpha: int = 255):
    if row < 0:
        return
    rect = _block_rect(col, row)
    if alpha < 255:
        s = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
        s.fill((*color, alpha))
        surf.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect)
        pygame.draw.rect(surf, BLACK, rect, 1)   # 셀 테두리


def _draw_mini_piece(surf: pygame.Surface, piece, topleft: tuple, cell: int = 24):
    """사이드바용 작은 피스 미리보기"""
    if piece is None:
        return
    ox, oy = topleft
    s = piece.shape
    # 중앙 정렬
    pw = len(s[0]) * cell
    ph = len(s)    * cell
    for r, row in enumerate(s):
        for c, val in enumerate(row):
            if val:
                rect = pygame.Rect(ox + c * cell, oy + r * cell, cell - 1, cell - 1)
                pygame.draw.rect(surf, piece.color, rect)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self._init_fonts()

    def _init_fonts(self):
        pygame.font.init()
        self.font_lg   = pygame.font.SysFont("consolas", 42, bold=True)
        self.font_md   = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_sm   = pygame.font.SysFont("consolas", 18)
        self.font_tiny = pygame.font.SysFont("consolas", 14)

    # ── 메인 드로우 ─────────────────────────────────────────
    def draw(self, game: Game):
        self.screen.fill(PANEL_BG)

        if game.state == State.MENU:
            self._draw_menu()
        elif game.state in (State.PLAYING, State.PAUSED):
            self._draw_board_bg()
            self._draw_locked(game)
            self._draw_ghost(game)
            self._draw_current(game)
            self._draw_grid_lines()
            self._draw_border()
            self._draw_sidebar(game)
            if game.state == State.PAUSED:
                self._draw_overlay("PAUSED", "Press P to resume")
        elif game.state == State.GAME_OVER:
            self._draw_board_bg()
            self._draw_locked(game)
            self._draw_grid_lines()
            self._draw_border()
            self._draw_sidebar(game)
            self._draw_overlay("GAME OVER", "Press R to restart  |  ESC: Menu")

        pygame.display.flip()

    # ── 보드 배경 ───────────────────────────────────────────
    def _draw_board_bg(self):
        pygame.draw.rect(
            self.screen, BLACK,
            (BOARD_OFFSET_X, BOARD_OFFSET_Y, PLAY_WIDTH, PLAY_HEIGHT)
        )

    def _draw_grid_lines(self):
        for r in range(ROWS + 1):
            y = BOARD_OFFSET_Y + r * BLOCK_SIZE
            pygame.draw.line(self.screen, DARK_GRAY,
                             (BOARD_OFFSET_X, y),
                             (BOARD_OFFSET_X + PLAY_WIDTH, y))
        for c in range(COLS + 1):
            x = BOARD_OFFSET_X + c * BLOCK_SIZE
            pygame.draw.line(self.screen, DARK_GRAY,
                             (x, BOARD_OFFSET_Y),
                             (x, BOARD_OFFSET_Y + PLAY_HEIGHT))

    def _draw_border(self):
        pygame.draw.rect(
            self.screen, BORDER_COLOR,
            (BOARD_OFFSET_X - 2, BOARD_OFFSET_Y - 2,
             PLAY_WIDTH + 4, PLAY_HEIGHT + 4), 2
        )

    # ── 고정 블록 ────────────────────────────────────────────
    def _draw_locked(self, game: Game):
        for r, row in enumerate(game.board.grid):
            for c, color in enumerate(row):
                if color:
                    _draw_block(self.screen, color, c, r)

    # ── 고스트 피스 ─────────────────────────────────────────
    def _draw_ghost(self, game: Game):
        gy = game.ghost_y
        if gy == game.current.y:
            return
        for col, row in game.current.cells(oy=gy):
            _draw_block(self.screen, game.current.color, col, row, alpha=60)

    # ── 현재 피스 ────────────────────────────────────────────
    def _draw_current(self, game: Game):
        for col, row in game.current.cells():
            _draw_block(self.screen, game.current.color, col, row)

    # ── 사이드바 ─────────────────────────────────────────────
    def _draw_sidebar(self, game: Game):
        sx = BOARD_OFFSET_X + PLAY_WIDTH + 20
        sy = BOARD_OFFSET_Y

        def label(text, y, font=None, color=LIGHT_GRAY):
            f = font or self.font_sm
            s = f.render(text, True, color)
            self.screen.blit(s, (sx, y))
            return s.get_height()

        # 타이틀
        self.screen.blit(
            self.font_lg.render("TETRIS", True, TITLE_COLOR),
            (BOARD_OFFSET_X, 18)
        )

        y = sy

        # SCORE
        label("SCORE", y, self.font_tiny, GRAY); y += 16
        label(f"{game.score}", y, self.font_md, WHITE); y += 30

        # HIGH SCORE
        label("BEST", y, self.font_tiny, GRAY); y += 16
        label(f"{game.high_score}", y, self.font_md, YELLOW); y += 30

        # LEVEL
        label("LEVEL", y, self.font_tiny, GRAY); y += 16
        label(f"{game.level}", y, self.font_md, WHITE); y += 30

        # LINES
        label("LINES", y, self.font_tiny, GRAY); y += 16
        label(f"{game.lines}", y, self.font_md, WHITE); y += 36

        # NEXT
        label("NEXT", y, self.font_tiny, GRAY); y += 18
        _draw_mini_piece(self.screen, game.next_piece, (sx, y))
        y += 90

        # HOLD
        label("HOLD", y, self.font_tiny, GRAY); y += 18
        if game.held_piece:
            col = GRAY if game.hold_used else game.held_piece.color
            p = game.held_piece.copy()
            p.color = col  # type: ignore[assignment]
            _draw_mini_piece(self.screen, p, (sx, y))
        y += 90

        # 키 가이드
        keys = [
            ("←→",   "Move"),
            ("↑",    "Rotate CW"),
            ("Z",    "Rotate CCW"),
            ("↓",    "Soft Drop"),
            ("Space","Hard Drop"),
            ("C",    "Hold"),
            ("P",    "Pause"),
            ("R",    "Restart"),
            ("ESC",  "Menu"),
        ]
        label("KEYS", y, self.font_tiny, GRAY); y += 16
        for key, action in keys:
            line = f"{key:<7}{action}"
            label(line, y, self.font_tiny, KEY_COLOR)
            y += 15

    # ── 오버레이 (PAUSED / GAME OVER) ───────────────────────
    def _draw_overlay(self, title: str, subtitle: str):
        overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (BOARD_OFFSET_X, BOARD_OFFSET_Y))

        t = self.font_lg.render(title, True, WHITE)
        cx = BOARD_OFFSET_X + PLAY_WIDTH // 2 - t.get_width() // 2
        cy = BOARD_OFFSET_Y + PLAY_HEIGHT // 2 - 40
        self.screen.blit(t, (cx, cy))

        s = self.font_sm.render(subtitle, True, LIGHT_GRAY)
        cx2 = BOARD_OFFSET_X + PLAY_WIDTH // 2 - s.get_width() // 2
        self.screen.blit(s, (cx2, cy + 50))

    # ── 메뉴 화면 ────────────────────────────────────────────
    def _draw_menu(self):
        cx = WINDOW_WIDTH // 2

        def center(text, y, font, color=WHITE):
            s = font.render(text, True, color)
            self.screen.blit(s, (cx - s.get_width() // 2, y))

        center("TETRIS", 140, self.font_lg, TITLE_COLOR)
        center("Press ENTER or SPACE to Start", 230, self.font_sm, LIGHT_GRAY)
        center("Built with Python + Pygame", 270, self.font_tiny, GRAY)

        keys = [
            "←/→  Move        ↑  Rotate CW    Z  Rotate CCW",
            "↓  Soft Drop    Space  Hard Drop    C  Hold",
            "P  Pause / Resume    R  Restart    ESC  Menu",
        ]
        for i, line in enumerate(keys):
            center(line, 360 + i * 22, self.font_tiny, KEY_COLOR)
