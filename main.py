

import pygame
import sys
import random
import math
import heapq
import asyncio
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


class GameState(Enum):
    MENU        = auto()
    PLAYING     = auto()
    DEAD_SCREEN = auto()
    LEVEL_CLEAR = auto()
    GAME_OVER   = auto()


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


class Coin:
    def __init__(self, tile_x, tile_y):
        self.tile = (tile_x, tile_y)
        self.collected = False
        self.pulse = random.uniform(0, 2 * math.pi)

    def update(self):
        self.pulse = (self.pulse + 0.05) % (2 * math.pi)

    def draw(self, surf, hud_offset):
        if self.collected:
            return
        cx = self.tile[0] * TILE + TILE // 2
        cy = self.tile[1] * TILE + TILE // 2 + hud_offset
        r  = int(5 + 2 * math.sin(self.pulse))
        pygame.draw.circle(surf, C_COIN, (cx, cy), r)
        pygame.draw.circle(surf, (255, 240, 160), (cx, cy), max(2, r - 2))


class Player:
    def __init__(self, tile_x, tile_y):
        self.tile = [tile_x, tile_y]
        self.hp   = PLAYER_MAX_HP
        self.score = 0
        self.dropped_souls = 0
        self.move_cd  = 0
        self.dmg_flash = 0
        self.pulse = 0.0

    def move(self, dx, dy, grid):
        if self.move_cd > 0:
            return
        nx = self.tile[0] + dx
        ny = self.tile[1] + dy
        if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
            self.tile[0] = nx
            self.tile[1] = ny
            self.move_cd = PLAYER_SPEED

    def update(self):
        if self.move_cd > 0:
            self.move_cd -= 1
        if self.dmg_flash > 0:
            self.dmg_flash -= 1
        self.pulse = (self.pulse + 0.07) % (2 * math.pi)

    def take_damage(self, amount):
        self.hp -= amount
        self.dmg_flash = 15

    def draw(self, surf, hud_offset):
        cx = self.tile[0] * TILE + TILE // 2
        cy = self.tile[1] * TILE + TILE // 2 + hud_offset

        if self.dmg_flash > 0:
            glow_s = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 80, 80, 100), (TILE, TILE), 18)
            surf.blit(glow_s, (cx - TILE, cy - TILE))

        color = C_PLAYER if self.dmg_flash == 0 else (255, 150, 150)
        pygame.draw.circle(surf, color, (cx, cy), 10)
        pygame.draw.circle(surf, (100, 120, 180), (cx, cy), 10, 2)
        pygame.draw.circle(surf, C_PLAYER_EYE, (cx - 3, cy - 2), 2)
        pygame.draw.circle(surf, C_PLAYER_EYE, (cx + 3, cy - 2), 2)

        if self.dropped_souls > 0:
            r = int(12 + 3 * math.sin(self.pulse))
            aura = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*C_SOUL_A, 50), (TILE, TILE), r)
            surf.blit(aura, (cx - TILE, cy - TILE))



class Enemy:
    def __init__(self, tile_x, tile_y):
        self.tile  = [tile_x, tile_y]
        self.path  = []
        self.path_timer = 0
        self.move_cd = 8
        self.pulse   = random.uniform(0, math.pi * 2)

    def update(self, grid, player_tile, occupied_tiles):
        self.pulse = (self.pulse + 0.09) % (2 * math.pi)
        if self.move_cd > 0:
            self.move_cd -= 1

        self.path_timer -= 1
        if self.path_timer <= 0:
            self.path = astar(grid, tuple(self.tile), tuple(player_tile))
            self.path_timer = ENEMY_A_STAR_INTERVAL

        if self.move_cd <= 0 and self.path:
            next_tile = self.path[0]
            if list(next_tile) != self.tile:
                if next_tile not in occupied_tiles:
                    self.tile = list(next_tile)
                    self.path.pop(0)
                    self.move_cd = 8
            else:
                self.path.pop(0)
                self.move_cd = 8

    def draw(self, surf, hud_offset):
        cx = self.tile[0] * TILE + TILE // 2
        cy = self.tile[1] * TILE + TILE // 2 + hud_offset
        glow_s = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
        gr = int(14 + 4 * math.sin(self.pulse))
        pygame.draw.circle(glow_s, (200, 30, 30, 60), (TILE, TILE), gr)
        surf.blit(glow_s, (cx - TILE, cy - TILE))
        pygame.draw.rect(surf, (80, 20, 20), (cx - 9, cy - 9, 18, 18), border_radius=3)
        pygame.draw.rect(surf, C_ENEMY,     (cx - 9, cy - 9, 18, 18), 2, border_radius=3)
        eye_r = int(2 + math.sin(self.pulse))
        pygame.draw.circle(surf, C_ENEMY_EYE, (cx - 3, cy - 2), eye_r)
        pygame.draw.circle(surf, C_ENEMY_EYE, (cx + 3, cy - 2), eye_r)



def draw_hud(surf, player, level, font, small_font, soul_orb, hud_rect):
    pygame.draw.rect(surf, C_HUD_BG, hud_rect)
    pygame.draw.line(surf, (50, 50, 70),
                     (0, hud_rect.bottom - 1), (hud_rect.right, hud_rect.bottom - 1), 1)

    bar_x, bar_y = 12, 14
    bar_w, bar_h = 160, 14
    hp_pct = player.hp / PLAYER_MAX_HP
    pygame.draw.rect(surf, C_HP_BG,  (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(surf, C_HP_BAR, (bar_x, bar_y, int(bar_w * hp_pct), bar_h), border_radius=4)
    pygame.draw.rect(surf, (180, 60, 60), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
    hp_label = small_font.render(f"Health: {player.hp} / {PLAYER_MAX_HP}", True, (220, 170, 170))
    surf.blit(hp_label, (bar_x + 4, bar_y))

    score_txt = font.render(f"Score: {player.score}", True, C_SCORE_TXT)
    surf.blit(score_txt, (200, 10))

    if soul_orb and soul_orb.active:
        r = int(8 + 2 * math.sin(soul_orb.pulse))
        sx, sy = 200, 40
        glow = pygame.Surface((40, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*C_SOUL_A, 80), (15, 15), r + 4)
        surf.blit(glow, (sx - 5, sy - 5))
        pygame.draw.circle(surf, C_SOUL_B, (sx + 10, sy + 7), r)
        soul_txt = small_font.render(f"Lost Souls: {soul_orb.value}  (Return to recover!)", True, C_SOUL_B)
        surf.blit(soul_txt, (sx + 22, sy))

    lvl_txt = font.render(f"Level {level}", True, C_EXIT)
    surf.blit(lvl_txt, (surf.get_width() - 110, 10))


def draw_centered_text(surf, text, font, color, cy, shadow=True):
    if shadow:
        s = font.render(text, True, (0, 0, 0))
        surf.blit(s, (surf.get_width() // 2 - s.get_width() // 2 + 2, cy + 2))
    t = font.render(text, True, color)
    surf.blit(t, (surf.get_width() // 2 - t.get_width() // 2, cy))


def draw_menu(surf, big_font, med_font, small_font, tick):
    surf.fill(C_BG)
    for y in range(0, surf.get_height(), TILE):
        for x in range(0, surf.get_width(), TILE):
            if (x // TILE + y // TILE) % 2 == 0:
                pygame.draw.rect(surf, C_FLOOR2, (x, y, TILE, TILE))

    title_y = surf.get_height() // 2 - 100
    glow_r = int(180 + 30 * math.sin(tick * 0.05))
    glow_surf = pygame.Surface((500, 100), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_surf, (*C_MENU_GLOW, 40), (0, 0, 500, 100))
    surf.blit(glow_surf, (surf.get_width() // 2 - 250, title_y - 10))

    draw_centered_text(surf, "HOLLOW-HUNGER", big_font, C_WHITE, title_y)
    draw_centered_text(surf, "Inspired by the great Hidetaka Miyazaki.", med_font, (150, 150, 180), title_y + 55)

    blink = (tick // 30) % 2 == 0
    if blink:
        draw_centered_text(surf, "Press  ENTER  to Start", small_font, C_GOLD, title_y + 110)

    draw_centered_text(surf, "Move: WASD / Arrow Keys     Collect Coins     Reach the Exit     Avoid Enemies",
                       small_font, (100, 100, 130), surf.get_height() - 36)


def draw_you_died(surf, big_font, med_font, alpha):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, min(200, alpha)))
    surf.blit(overlay, (0, 0))

    a_clamped = min(255, alpha)
    col = (min(255, a_clamped), max(0, 60 - alpha // 4), max(0, 60 - alpha // 4))
    draw_centered_text(surf, "Y O U   D I E D", big_font, col, surf.get_height() // 2 - 40)
    if alpha > 180:
        draw_centered_text(surf, "Your souls dropped at the death spot — go back to recover them!",
                           med_font, (180, 100, 100), surf.get_height() // 2 + 30)


def draw_level_clear(surf, big_font, med_font, alpha, level):
    overlay = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, min(180, alpha)))
    surf.blit(overlay, (0, 0))
    draw_centered_text(surf, "LEVEL CLEARED!", big_font, C_EXIT, surf.get_height() // 2 - 40)
    if alpha > 120:
        draw_centered_text(surf, f"Proceeding to Level {level + 1}...",
                           med_font, (180, 255, 210), surf.get_height() // 2 + 30)


def draw_game_over(surf, big_font, med_font, small_font, score):
    surf.fill(C_BG)
    draw_centered_text(surf, "GAME OVER", big_font, C_RED, surf.get_height() // 2 - 80)
    draw_centered_text(surf, f"Your Final Score:  {score}", med_font, C_SCORE_TXT,
                       surf.get_height() // 2 - 10)
    draw_centered_text(surf, "Press R to Play Again   |   Press ESC to Quit",
                       small_font, (140, 140, 160), surf.get_height() // 2 + 50)


def draw_dpad(surf):
    sw, sh = surf.get_width(), surf.get_height()
    cx, cy = 100, sh - 100
    off = 45
    r = 30
    
    dpad_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
    
    def draw_btn(bx, by, label):
        pygame.draw.circle(dpad_surf, (200, 200, 200, 60), (bx, by), r)
        pygame.draw.circle(dpad_surf, (255, 255, 255, 100), (bx, by), r, 2)
        font = pygame.font.SysFont("consolas", 20, bold=True)
        txt = font.render(label, True, (255, 255, 255, 150))
        dpad_surf.blit(txt, (bx - txt.get_width()//2, by - txt.get_height()//2))

    draw_btn(100, 100 - off, "W")
    draw_btn(100, 100 + off, "S")
    draw_btn(100 - off, 100, "A")
    draw_btn(100 + off, 100, "D")
    
    surf.blit(dpad_surf, (cx - 100, cy - 100))


class ExitPortal:
    def __init__(self, tile_x, tile_y):
        self.tile  = (tile_x, tile_y)
        self.pulse = 0.0

    def update(self):
        self.pulse = (self.pulse + 0.06) % (2 * math.pi)

    def draw(self, surf, hud_offset):
        cx = self.tile[0] * TILE + TILE // 2
        cy = self.tile[1] * TILE + TILE // 2 + hud_offset
        r  = int(11 + 4 * math.sin(self.pulse))

        glow = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*C_EXIT, 60), (TILE, TILE), r + 6)
        surf.blit(glow, (cx - TILE, cy - TILE))
        pygame.draw.circle(surf, C_EXIT, (cx, cy), r)
        pygame.draw.circle(surf, (220, 255, 245), (cx, cy), max(4, r - 4))



class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Hollow-Hunger")

        self.base_w = BASE_MAZE_W
        self.base_h = BASE_MAZE_H

        self.screen = pygame.display.set_mode(
            (self.base_w * TILE, self.base_h * TILE + HUD_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)

        self.clock    = pygame.time.Clock()
        self.big_font  = pygame.font.SysFont("consolas", 48, bold=True)
        self.med_font  = pygame.font.SysFont("consolas", 26, bold=True)
        self.small_font= pygame.font.SysFont("consolas", 16)
        self.font      = pygame.font.SysFont("consolas", 20, bold=True)

        self.level = 1
        self.state = GameState.MENU
        self.tick  = 0
        self.overlay_alpha = 0
        self.touches = {}
        self.show_dpad = False

        self.grid    = []
        self.player  = None
        self.enemies = []
        self.coins   = []
        self.soul_orb = None
        self.portal   = None
        self.enemy_damage_timer = {}



    def load_level(self):
        cols = self.base_w + (self.level - 1) * 2
        rows = self.base_h + (self.level - 1) * 2
        cols = min(cols, 41)
        rows = min(rows, 31)
        if cols % 2 == 0: cols += 1
        if rows % 2 == 0: rows += 1

        self.screen = pygame.display.set_mode(
            (cols * TILE, rows * TILE + HUD_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)

        sys.setrecursionlimit(cols * rows * 4)
        self.grid = generate_maze(cols, rows)

        floors = open_tiles(self.grid)
        random.shuffle(floors)

        self.player = Player(1, 1)

        far = max(floors, key=lambda t: abs(t[0] - 1) + abs(t[1] - 1))
        self.portal = ExitPortal(*far)
        floors.remove(far)

        num_enemies = ENEMY_COUNT_BASE + self.level - 1
        self.enemies = []
        self.enemy_damage_timer = {}
        placed = 0
        for t in floors:
            if placed >= num_enemies:
                break
            if abs(t[0] - 1) + abs(t[1] - 1) > 6:
                self.enemies.append(Enemy(*t))
                placed += 1

        num_coins = COIN_COUNT_BASE + self.level
        used = {(1, 1), far} | {tuple(e.tile) for e in self.enemies}
        self.coins = []
        for t in floors:
            if len(self.coins) >= num_coins:
                break
            if t not in used:
                self.coins.append(Coin(*t))
                used.add(t)

        self.soul_orb = None
        self.overlay_alpha = 0



    async def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.tick += 1
            self._handle_events()
            self._update()
            self._draw()
            await asyncio.sleep(0)



    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            ftype = getattr(event, 'type', None)
            
            if ftype == getattr(pygame, 'FINGERDOWN', None) or ftype == getattr(pygame, 'FINGERMOTION', None):
                self.show_dpad = True
                sw, sh = self.screen.get_width(), self.screen.get_height()
                self.touches[event.finger_id] = (event.x * sw, event.y * sh)
            elif ftype == getattr(pygame, 'FINGERUP', None):
                self.touches.pop(event.finger_id, None)

            is_tap = (ftype == pygame.MOUSEBUTTONDOWN or ftype == getattr(pygame, 'FINGERDOWN', None))

            if event.type == pygame.KEYDOWN:
                self.show_dpad = False
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if self.state == GameState.MENU:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.level = 1
                        self.load_level()
                        self.state = GameState.PLAYING

                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_h and self.player:
                        self.player.hp = PLAYER_MAX_HP

                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.level = 1
                        self.load_level()
                        self.state = GameState.PLAYING
                        
            if is_tap:
                if self.state == GameState.MENU:
                    self.level = 1
                    self.load_level()
                    self.state = GameState.PLAYING
                elif self.state == GameState.GAME_OVER:
                    self.level = 1
                    self.load_level()
                    self.state = GameState.PLAYING

    def _get_move_input(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx =  1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy = -1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy =  1

        sw, sh = self.screen.get_width(), self.screen.get_height()
        cx, cy = 100, sh - 100
        off = 45
        r = 30

        def check_pos(px, py):
            nonlocal dx, dy
            if math.hypot(px - cx, py - (cy - off)) < r: dy = -1
            elif math.hypot(px - cx, py - (cy + off)) < r: dy = 1
            elif math.hypot(px - (cx - off), py - cy) < r: dx = -1
            elif math.hypot(px - (cx + off), py - cy) < r: dx = 1

        if self.show_dpad:
            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                check_pos(mx, my)

            for px, py in self.touches.values():
                check_pos(px, py)

        return dx, dy



    def _update(self):
        if self.state == GameState.MENU:
            return

        if self.state == GameState.GAME_OVER:
            return

        if self.state == GameState.DEAD_SCREEN:
            self.overlay_alpha = min(self.overlay_alpha + 4, 255)
            if self.overlay_alpha >= 255:
                self.player = Player(1, 1)
                self.player.hp = PLAYER_MAX_HP
                self.state = GameState.PLAYING
                self.overlay_alpha = 0
            return

        if self.state == GameState.LEVEL_CLEAR:
            self.overlay_alpha = min(self.overlay_alpha + 3, 255)
            if self.overlay_alpha >= 255:
                score_carry = self.player.score if self.player else 0
                self.level += 1
                self.load_level()
                self.player.score = score_carry
                self.state = GameState.PLAYING
            return

        if self.state != GameState.PLAYING:
            return

        dx, dy = self._get_move_input()
        self.player.move(dx, dy, self.grid)
        self.player.update()

        for coin in self.coins:
            coin.update()
            if not coin.collected and tuple(self.player.tile) == coin.tile:
                coin.collected = True
                self.player.score += COIN_VALUE

        if self.soul_orb and self.soul_orb.active:
            self.soul_orb.update()
            if tuple(self.player.tile) == self.soul_orb.tile:
                self.player.score += self.soul_orb.value
                self.player.dropped_souls = 0
                self.soul_orb.active = False

        self.portal.update()
        if tuple(self.player.tile) == self.portal.tile:
            self.state = GameState.LEVEL_CLEAR
            self.overlay_alpha = 0
            return

        for i, enemy in enumerate(self.enemies):
            occupied = {tuple(e.tile) for j, e in enumerate(self.enemies) if j != i}
            enemy.update(self.grid, self.player.tile, occupied)

            if tuple(enemy.tile) == tuple(self.player.tile):
                cd = self.enemy_damage_timer.get(i, 0)
                if cd <= 0:
                    self.player.take_damage(ENEMY_DAMAGE)
                    self.enemy_damage_timer[i] = ENEMY_DAMAGE_CD
                else:
                    self.enemy_damage_timer[i] = cd - 1
            else:
                if i in self.enemy_damage_timer and self.enemy_damage_timer[i] > 0:
                    self.enemy_damage_timer[i] -= 1

        if self.player.hp <= 0:
            soul_val = self.player.score
            self.soul_orb = SoulOrb(self.player.tile[0], self.player.tile[1], soul_val)
            self.player.score = 0
            self.state = GameState.DEAD_SCREEN
            self.overlay_alpha = 0



    def _draw(self):
        surf = self.screen

        if self.state == GameState.MENU:
            draw_menu(surf, self.big_font, self.med_font, self.small_font, self.tick)
            pygame.display.flip()
            return

        if self.state == GameState.GAME_OVER:
            draw_game_over(surf, self.big_font, self.med_font, self.small_font,
                           self.player.score if self.player else 0)
            pygame.display.flip()
            return

        surf.fill(C_BG)

        cols = len(self.grid[0])
        rows = len(self.grid)
        for r in range(rows):
            for c in range(cols):
                rx = c * TILE
                ry = r * TILE + HUD_HEIGHT
                if self.grid[r][c] == 1:
                    pygame.draw.rect(surf, C_WALL, (rx, ry, TILE, TILE))
                    pygame.draw.rect(surf, C_WALL_EDGE, (rx, ry, TILE, TILE), 1)
                else:
                    col = C_FLOOR if (r + c) % 2 == 0 else C_FLOOR2
                    pygame.draw.rect(surf, col, (rx, ry, TILE, TILE))

        if self.soul_orb and self.soul_orb.active:
            self.soul_orb.draw(surf, HUD_HEIGHT)

        for coin in self.coins:
            coin.draw(surf, HUD_HEIGHT)

        self.portal.draw(surf, HUD_HEIGHT)

        for enemy in self.enemies:
            enemy.draw(surf, HUD_HEIGHT)

        self.player.draw(surf, HUD_HEIGHT)

        hud_rect = pygame.Rect(0, 0, surf.get_width(), HUD_HEIGHT)
        draw_hud(surf, self.player, self.level, self.font, self.small_font,
                 self.soul_orb, hud_rect)

        if self.state == GameState.PLAYING and self.show_dpad:
            draw_dpad(surf)

        if self.state == GameState.DEAD_SCREEN:
            draw_you_died(surf, self.big_font, self.med_font, self.overlay_alpha)
            

        if self.state == GameState.LEVEL_CLEAR:
            draw_level_clear(surf, self.big_font, self.med_font, self.overlay_alpha, self.level)

        pygame.display.flip()



if __name__ == "__main__":
    asyncio.run(Game().run())

