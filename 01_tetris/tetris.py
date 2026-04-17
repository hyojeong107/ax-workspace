import pygame
import random

# Initialize Pygame
pygame.init()

# Screen dimensions
PLAY_WIDTH, PLAY_HEIGHT = 300, 600
BLOCK_SIZE = 30
TOP_LEFT_X = 50
TOP_LEFT_Y = 50

# Total window dimensions
WIDTH, HEIGHT = 600, 700

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)

SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0, 0], [1, 1, 1]],  # L
    [[0, 0, 1], [1, 1, 1]],  # J
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]]   # Z
]

COLORS = [
    (0, 255, 255),  # Cyan for I
    (255, 255, 0),  # Yellow for O
    (128, 0, 128),  # Purple for T
    (255, 165, 0),  # Orange for L
    (0, 0, 255),    # Blue for J
    (0, 255, 0),    # Green for S
    (255, 0, 0)     # Red for Z
]

class Tetris:
    def __init__(self):
        self.cols = PLAY_WIDTH // BLOCK_SIZE
        self.rows = PLAY_HEIGHT // BLOCK_SIZE
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.score = 0
        self.game_over = False
        self.next_shape_idx = random.randint(0, len(SHAPES) - 1)
        self.new_piece()

    def new_piece(self):
        self.current_shape_idx = self.next_shape_idx
        self.current_shape = SHAPES[self.current_shape_idx]
        self.current_color = COLORS[self.current_shape_idx]
        
        self.next_shape_idx = random.randint(0, len(SHAPES) - 1)
        
        self.piece_x = self.cols // 2 - len(self.current_shape[0]) // 2
        self.piece_y = 0

        if not self.valid_move(self.current_shape, self.piece_x, self.piece_y):
            self.game_over = True

    def valid_move(self, shape, offset_x, offset_y):
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = offset_x + x
                    new_y = offset_y + y
                    if new_x < 0 or new_x >= self.cols or new_y >= self.rows:
                        return False
                    if new_y >= 0 and self.grid[new_y][new_x]:
                        return False
        return True

    def move(self, dx, dy):
        if self.valid_move(self.current_shape, self.piece_x + dx, self.piece_y + dy):
            self.piece_x += dx
            self.piece_y += dy
            return True
        return False

    def drop(self):
        if not self.move(0, 1):
            self.lock_piece()
            self.clear_lines()
            self.new_piece()

    def hard_drop(self):
        while self.move(0, 1):
            pass
        self.lock_piece()
        self.clear_lines()
        self.new_piece()

    def rotate(self):
        # Transpose and reverse rows
        rotated = [list(row) for row in zip(*self.current_shape[::-1])]
        if self.valid_move(rotated, self.piece_x, self.piece_y):
            self.current_shape = rotated

    def lock_piece(self):
        for y, row in enumerate(self.current_shape):
            for x, cell in enumerate(row):
                if cell:
                    if self.piece_y + y >= 0:
                        self.grid[self.piece_y + y][self.piece_x + x] = self.current_color

    def clear_lines(self):
        lines_cleared = 0
        for y in range(len(self.grid) - 1, -1, -1):
            if all(self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [0 for _ in range(self.cols)])
                lines_cleared += 1
        
        if lines_cleared > 0:
            scores = [0, 100, 300, 500, 800]
            self.score += scores[min(lines_cleared, 4)]

def draw_window(screen, game):
    screen.fill(BLACK)
    
    # Draw title
    font = pygame.font.SysFont('comicsans', 60)
    label = font.render('TETRIS', 1, WHITE)
    screen.blit(label, (TOP_LEFT_X + PLAY_WIDTH / 2 - label.get_width() / 2, 10))

    # Draw current piece
    if not game.game_over:
        for y, row in enumerate(game.current_shape):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(screen, game.current_color, 
                                     (TOP_LEFT_X + (game.piece_x + x) * BLOCK_SIZE, 
                                      TOP_LEFT_Y + (game.piece_y + y) * BLOCK_SIZE, 
                                      BLOCK_SIZE, BLOCK_SIZE), 0)

    # Draw grid blocks
    for y in range(game.rows):
        for x in range(game.cols):
            if game.grid[y][x]:
                pygame.draw.rect(screen, game.grid[y][x], 
                                 (TOP_LEFT_X + x * BLOCK_SIZE, 
                                  TOP_LEFT_Y + y * BLOCK_SIZE, 
                                  BLOCK_SIZE, BLOCK_SIZE), 0)

    # Draw grid lines
    for i in range(game.rows + 1):
        pygame.draw.line(screen, GRAY, (TOP_LEFT_X, TOP_LEFT_Y + i * BLOCK_SIZE), 
                         (TOP_LEFT_X + PLAY_WIDTH, TOP_LEFT_Y + i * BLOCK_SIZE))
    for j in range(game.cols + 1):
        pygame.draw.line(screen, GRAY, (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y), 
                         (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y + PLAY_HEIGHT))
    
    # Draw play area border
    pygame.draw.rect(screen, RED, (TOP_LEFT_X, TOP_LEFT_Y, PLAY_WIDTH, PLAY_HEIGHT), 5)

    # Draw score
    font = pygame.font.SysFont('comicsans', 30)
    score_label = font.render(f'Score: {game.score}', 1, WHITE)
    sx = TOP_LEFT_X + PLAY_WIDTH + 50
    sy = TOP_LEFT_Y + PLAY_HEIGHT / 2 - 100
    screen.blit(score_label, (sx, sy))

    # Draw next piece
    next_label = font.render('Next Shape:', 1, WHITE)
    screen.blit(next_label, (sx, sy + 50))
    next_shape = SHAPES[game.next_shape_idx]
    next_color = COLORS[game.next_shape_idx]
    
    for y, row in enumerate(next_shape):
        for x, cell in enumerate(row):
            if cell:
                pygame.draw.rect(screen, next_color, 
                                 (sx + x * BLOCK_SIZE, sy + 100 + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 0)

    # Game Over Text
    if game.game_over:
        over_label = font.render('GAME OVER', 1, WHITE)
        screen.blit(over_label, (TOP_LEFT_X + PLAY_WIDTH / 2 - over_label.get_width() / 2, TOP_LEFT_Y + PLAY_HEIGHT / 2))

    pygame.display.update()

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    game = Tetris()

    fall_time = 0
    fall_speed = 500  # ms

    running = True
    while running:
        dt = clock.tick(60)
        fall_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN and not game.game_over:
                if event.key == pygame.K_LEFT:
                    game.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.move(1, 0)
                elif event.key == pygame.K_DOWN:
                    game.move(0, 1)
                elif event.key == pygame.K_UP:
                    game.rotate()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()

        if fall_time >= fall_speed and not game.game_over:
            game.drop()
            fall_time = 0

        draw_window(screen, game)

    pygame.quit()

if __name__ == '__main__':
    main()
