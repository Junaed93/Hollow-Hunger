import pygame
import sys
import random
import math
import heapq
from enum import Enum, auto


TILE  = 32
FPS   = 60

BASE_MAZE_W = 21
BASE_MAZE_H = 15

HUD_HEIGHT = 64


C_BG          = (10,  10,  15)
C_WALL        = (45,  45,  55)
C_WALL_EDGE   = (30,  30,  38)
C_FLOOR       = (22,  22,  30)
C_FLOOR2      = (18,  18,  25)
C_PLAYER      = (200, 220, 255)
C_PLAYER_EYE  = (120, 200, 255)
C_ENEMY       = (200, 40,  40)
C_ENEMY_EYE   = (255, 100, 50)
C_COIN        = (255, 210, 60)
C_SOUL_A      = (120, 180, 255)
C_SOUL_B      = (200, 230, 255)
C_EXIT        = (80,  255, 180)
C_HUD_BG      = (8,   8,   14)
C_HP_BAR      = (200, 60,  60)
C_HP_BG       = (60,  20,  20)
C_SCORE_TXT   = (220, 190, 120)
C_WHITE       = (240, 240, 240)
C_RED         = (220, 50,  50)
C_GOLD        = (255, 215, 70)
C_DARK_GOLD   = (180, 140, 30)
C_MENU_GLOW   = (80,  120, 200)

PLAYER_MAX_HP   = 200
PLAYER_SPEED    = 5
ENEMY_A_STAR_INTERVAL = 20
COIN_VALUE      = 10
ENEMY_DAMAGE    = 25
ENEMY_DAMAGE_CD = 60
ENEMY_COUNT_BASE = 2
COIN_COUNT_BASE  = 8


def generate_maze(cols, rows):
    """Return 2D list: 0=floor, 1=wall. cols & rows must be odd."""
    grid = [[1] * cols for _ in range(rows)]

    def carve(cx, cy):
        dirs = [(0, -2), (0, 2), (-2, 0), (2, 0)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 1:
                grid[cy + dy // 2][cx + dx // 2] = 0
                grid[ny][nx] = 0
                carve(nx, ny)

    grid[1][1] = 0
    carve(1, 1)
    return grid


def open_tiles(grid):
    """Return list of (col, row) tuples that are floor."""
    result = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == 0:
                result.append((c, r))
    return result



def astar(grid, start, goal):
    """
    Find shortest path on grid from start to goal (tile coords).
    Returns list of (col, row) tiles, or [] if no path.
    """
    rows = len(grid)
    cols = len(grid[0])

    def h(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        cx, cy = current
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] == 0:
                ng = g[current] + 1
                nb = (nx, ny)
                if ng < g.get(nb, float('inf')):
                    g[nb] = ng
                    came_from[nb] = current
                    f = ng + h(nb, goal)
                    heapq.heappush(open_set, (f, nb))
    return []



class SoulOrb:
    def __init__(self, tile_x, tile_y, value):
        self.tile = (tile_x, tile_y)
        self.value = value
        self.active = True
        self.pulse = 0.0

    def update(self):
        self.pulse = (self.pulse + 0.08) % (2 * math.pi)

    def draw(self, surf, hud_offset):
        if not self.active:
            return
        cx = self.tile[0] * TILE + TILE // 2
        cy = self.tile[1] * TILE + TILE // 2 + hud_offset
        r  = int(7 + 3 * math.sin(self.pulse))
        glow_surf = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*C_SOUL_A, 60), (TILE, TILE), r + 6)
        surf.blit(glow_surf, (cx - TILE, cy - TILE))
        pygame.draw.circle(surf, C_SOUL_B, (cx, cy), r)
        pygame.draw.circle(surf, (240, 248, 255), (cx, cy), max(3, r - 3))

