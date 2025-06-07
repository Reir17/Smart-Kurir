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

class Button:
    def _init_(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
    def draw(self, surface):
        pygame.draw.rect(surface, (180, 180, 180), self.rect)
        label = font.render(self.text, True, (0, 0, 0))
        surface.blit(label, (self.rect.x + 5, self.rect.y + 5))
    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()

def draw_kurir(pos, direction):
    x, y = pos
    x += 0.5
    y += 0.5
    x = int(x)
    y = int(y)
    size = 10
    if direction == "UP":
        points = [(x, y - size), (x - size, y + size), (x + size, y + size)]
    elif direction == "DOWN":
        points = [(x, y + size), (x - size, y - size), (x + size, y - size)]
    elif direction == "LEFT":
        points = [(x - size, y), (x + size, y - size), (x + size, y + size)]
    elif direction == "RIGHT":
        points = [(x + size, y), (x - size, y - size), (x - size, y + size)]
    pygame.draw.polygon(screen, (255, 0, 0), points)

def draw_info():
    info_box_height = 30
    for i, line in enumerate(info_lines):
        y_pos = SCREEN_HEIGHT - (len(info_lines) - i) * info_box_height
        pygame.draw.rect(screen, (240, 240, 240), (10, y_pos, 180, info_box_height))
        pygame.draw.rect(screen, (150, 150, 150), (10, y_pos, 180, info_box_height), 2)
        label = font.render(line, True, (0, 0, 0))
        screen.blit(label, (15, y_pos + 5))

def render():
    screen.fill((200, 200, 200))
    for btn in buttons:
        btn.draw(screen)
    if map_surface:
        screen.blit(map_surface, (200, 0))
        if source_pos != (0, 0):
            pygame.draw.circle(screen, (255, 255, 0), (200 + source_pos[0], source_pos[1]), 6)
        if dest_pos != (0, 0):
            pygame.draw.circle(screen, (255, 0, 0), (200 + dest_pos[0], dest_pos[1]), 6)
        if kurir_pos != (0, 0):
            draw_kurir((200 + kurir_pos[0], kurir_pos[1]), kurir_dir)
    draw_info()
    pygame.display.flip()
