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

def random_road_position(image):
    while True:
        x = random.randint(0, image.width - 1)
        y = random.randint(0, image.height - 1)
        if is_road(image, (x, y)):
            return x, y

def update_direction(path, current_pos):
    global kurir_dir
    i = path.index(current_pos)
    if i + 1 < len(path):
        next_pos = path[i + 1]
        dx = next_pos[0] - current_pos[0]
        dy = next_pos[1] - current_pos[1]
        if dx == 1: kurir_dir = "RIGHT"
        elif dx == -1: kurir_dir = "LEFT"
        elif dy == -1: kurir_dir = "UP"
        elif dy == 1: kurir_dir = "DOWN"

def bfs(start, goal, image):
    queue = deque()
    queue.append((start, [start]))
    visited = set()
    visited.add(start)
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        for dx, dy in directions:
            nx, ny = current[0] + dx, current[1] + dy
            if (nx, ny) not in visited and is_road(image, (nx, ny)):
                queue.append(((nx, ny), path + [(nx, ny)]))
                visited.add((nx, ny))
    return None

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(start, goal, image):
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path
        for dx, dy in directions:
            neighbor = (current[0] + dx, current[1] + dy)
            if not is_road(image, neighbor):
                continue
            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))
    return None
