# main.py — 진입점 + 게임 루프

import sys
import pygame

from constants import WINDOW_WIDTH, WINDOW_HEIGHT, FPS
from game import Game
from renderer import Renderer
from input_handler import InputHandler


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Tetris")

    clock    = pygame.time.Clock()
    game     = Game()
    renderer = Renderer(screen)
    handler  = InputHandler()

    running = True
    while running:
        dt = clock.tick(FPS)   # ms

        running = handler.handle_events(game)
        handler.update(game, dt)
        game.update(dt)
        renderer.draw(game)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
