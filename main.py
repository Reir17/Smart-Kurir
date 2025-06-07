import pygame
import random
from pygame.locals import *
from tkinter import filedialog, Tk
from PIL import Image
from collections import deque
import heapq
import time

# inisialisasi layar
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
JALAN_COLOR_RANGE = [(90, 90, 90), (150, 150, 150)]

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Smart Kurir")
font = pygame.font.SysFont("arial", 24)

# variabel
map_image = None
map_surface = None
kurir_pos = (0, 0)
kurir_dir = "RIGHT"
source_pos = (0, 0)
dest_pos = (0, 0)
highlight_path = []
info_lines = []
click_state = 0  # 0=kurir, 1=source, 2=dest

def is_road(image, pos):
    x, y = pos
    if x < 0 or y < 0 or x >= image.width or y >= image.height:
        return False
    pixel = image.getpixel((x, y))
    return all(JALAN_COLOR_RANGE[0][i] <= pixel[i] <= JALAN_COLOR_RANGE[1][i] for i in range(3))
