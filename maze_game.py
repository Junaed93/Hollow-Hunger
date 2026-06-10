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


