# input_handler.py — pygame 이벤트 → game API 호출

import pygame
from game import Game, State


# DAS/ARR 설정 (ms)
DAS_DELAY  = 170   # 첫 반복까지 대기
ARR_RATE   = 50    # 반복 간격


class InputHandler:
    """
    DAS(Delayed Auto Shift) + ARR(Auto Repeat Rate) 구현:
    방향키를 누르고 있을 때 자연스러운 연속 이동을 제공한다.
    """

    def __init__(self):
        self._left_held  = 0   # ms
        self._right_held = 0
        self._down_held  = 0

    def handle_events(self, game: Game) -> bool:
        """
        False 반환 시 앱 종료.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if not self._on_keydown(event.key, game):
                    return False

            if event.type == pygame.KEYUP:
                self._on_keyup(event.key)

        return True

    def update(self, game: Game, dt: int):
        """매 프레임 DAS/ARR 처리"""
        if game.state != State.PLAYING:
            self._left_held = self._right_held = self._down_held = 0
            return

        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]:
            self._left_held += dt
            if self._left_held > DAS_DELAY:
                if (self._left_held - DAS_DELAY) % ARR_RATE < dt:
                    game.move(-1)
        else:
            self._left_held = 0

        if keys[pygame.K_RIGHT]:
            self._right_held += dt
            if self._right_held > DAS_DELAY:
                if (self._right_held - DAS_DELAY) % ARR_RATE < dt:
                    game.move(1)
        else:
            self._right_held = 0

        if keys[pygame.K_DOWN]:
            self._down_held += dt
            if self._down_held > DAS_DELAY:
                if (self._down_held - DAS_DELAY) % ARR_RATE < dt:
                    game.soft_drop()
        else:
            self._down_held = 0

    # ── 키 입력 (단발) ──────────────────────────────────────
    def _on_keydown(self, key: int, game: Game) -> bool:
        # 항상 처리
        if key == pygame.K_ESCAPE:
            if game.state in (State.PLAYING, State.PAUSED, State.GAME_OVER):
                game.state = State.MENU
            else:
                return False   # 메뉴에서 ESC → 종료
            return True

        # 메뉴
        if game.state == State.MENU:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                game.start()
            return True

        # 게임오버
        if game.state == State.GAME_OVER:
            if key == pygame.K_r:
                game.start()
            return True

        # 일시정지 토글
        if key == pygame.K_p:
            game.toggle_pause()
            return True

        if game.state == State.PAUSED:
            return True

        # 플레이 중
        if key == pygame.K_LEFT:
            game.move(-1)
            self._left_held = 0
        elif key == pygame.K_RIGHT:
            game.move(1)
            self._right_held = 0
        elif key == pygame.K_DOWN:
            game.soft_drop()
            self._down_held = 0
        elif key == pygame.K_UP:
            game.rotate(1)
        elif key == pygame.K_z:
            game.rotate(-1)
        elif key == pygame.K_SPACE:
            game.hard_drop()
        elif key == pygame.K_c:
            game.hold()
        elif key == pygame.K_r:
            game.start()

        return True

    def _on_keyup(self, key: int):
        if key == pygame.K_LEFT:
            self._left_held = 0
        elif key == pygame.K_RIGHT:
            self._right_held = 0
        elif key == pygame.K_DOWN:
            self._down_held = 0
