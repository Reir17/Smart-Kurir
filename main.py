import pygame
import sys
import random
import heapq
from tkinter import filedialog, Tk

# Inisialisasi awal
pygame.init()
info = pygame.display.Info()
INIT_WIDTH, INIT_HEIGHT = 800, 600
screen = pygame.display.set_mode((INIT_WIDTH, INIT_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Smart Kurir - Dynamic Map")

# Warna
JALAN_MIN = (90, 90, 90)
JALAN_MAX = (150, 150, 150)
UI_COLOR = (40, 40, 40)
BUTTON_COLOR = (80, 80, 80)
TEXT_COLOR = (200, 200, 200)
RED = (255, 0, 0)
GREEN = (0, 255, 0)

# Aset
try:
    kurir_img_ori = pygame.image.load("assets/segitiga.png").convert_alpha()
except Exception as e:
    print(f"Error loading assets: {e}")
    sys.exit()

# Font
font = pygame.font.SysFont("Arial", 24)

# State game
peta = None
original_peta = None
jalan_mask = None
kurir_pos = None
tujuan_pos = None
is_running = False
path = []
current_path_index = 0
current_width = INIT_WIDTH
current_height = INIT_HEIGHT


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(start, goal):
    if start == goal or not jalan_mask:
        return []

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        current = heapq.heappop(open_set)[1]

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy in [(1, 0), (-1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < original_peta.get_width() and 0 <= neighbor[1] < original_peta.get_height():
                if is_walkable(neighbor):
                    tentative_g_score = g_score.get(current, float('inf')) + 1
                    if tentative_g_score < g_score.get(neighbor, float('inf')):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g_score
                        f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None


def is_walkable(pos):
    color = original_peta.get_at(pos)
    if color == (255, 255, 255):
        return False
    return (JALAN_MIN[0] <= color[0] <= JALAN_MAX[0] and
            JALAN_MIN[1] <= color[1] <= JALAN_MAX[1] and
            JALAN_MIN[2] <= color[2] <= JALAN_MAX[2])


def is_safe_for_kurir(pos, kurir_size):
    x, y = pos
    offset = kurir_size // 2
    for dx in range(-offset, offset + 1):
        for dy in range(-offset, offset + 1):
            check_pos = (x + dx, y + dy)
            if not (0 <= check_pos[0] < original_peta.get_width() and 0 <= check_pos[1] < original_peta.get_height()):
                return False
            if not is_walkable(check_pos):
                return False
    return True


def load_map():
    global peta, original_peta, jalan_mask, current_width, current_height
    Tk().withdraw()
    try:
        file_path = filedialog.askopenfilename()
        if file_path:
            original_peta = pygame.image.load(file_path).convert()
            width = original_peta.get_width()
            height = original_peta.get_height()
            if not (1000 <= width <= 1500) or not (700 <= height <= 1000):
                print("Error: Ukuran peta harus 1000-1500 x 700-1000 pixel")
                return
            scale = min(info.current_w / width, info.current_h / height) * 0.8
            current_width = int(width * scale)
            current_height = int(height * scale)
            screen = pygame.display.set_mode((current_width, current_height), pygame.RESIZABLE)
            peta = pygame.transform.smoothscale(original_peta, (current_width, current_height))

            mask_surface = original_peta.copy()
            mask_surface.set_colorkey((0, 0, 0))
            for x in range(width):
                for y in range(height):
                    color = original_peta.get_at((x, y))
                    mask_surface.set_at((x, y), (255, 255, 255) if is_walkable((x, y)) else (0, 0, 0))
            jalan_mask = pygame.mask.from_surface(mask_surface)
            acak_posisi()
    except Exception as e:
        print(f"Error loading map: {e}")


def acak_posisi():
    global kurir_pos, tujuan_pos, path, current_path_index
    if not original_peta:
        return
    width, height = original_peta.get_size()
    while True:
        kurir_pos = (random.randint(0, width - 1), random.randint(0, height - 1))
        if is_walkable(kurir_pos) and is_safe_for_kurir(kurir_pos, 30):
            break
    while True:
        tujuan_pos = (random.randint(0, width - 1), random.randint(0, height - 1))
        if is_walkable(tujuan_pos) and is_safe_for_kurir(tujuan_pos, 30) and tujuan_pos != kurir_pos:
            break
    path = astar(kurir_pos, tujuan_pos)
    current_path_index = 0


def get_scaled_pos(pos):
    scale_x = current_width / original_peta.get_width()
    scale_y = current_height / original_peta.get_height()
    return (int(pos[0] * scale_x), int(pos[1] * scale_y))


def get_scaled_pos_centered(pos, size):
    scaled = get_scaled_pos(pos)
    return (scaled[0] - size // 2, scaled[1] - size // 2)


def get_kurir_direction():
    if current_path_index >= len(path):
        return "KANAN"
    next_pos = path[current_path_index]
    dx = next_pos[0] - kurir_pos[0]
    dy = next_pos[1] - kurir_pos[1]
    if dx > 0: return "KANAN"
    if dx < 0: return "KIRI"
    if dy < 0: return "ATAS"
    return "BAWAH"


def rotate_kurir(direction):
    return {
        "KANAN": kurir_img_ori,
        "KIRI": pygame.transform.rotate(kurir_img_ori, 180),
        "ATAS": pygame.transform.rotate(kurir_img_ori, 90),
        "BAWAH": pygame.transform.rotate(kurir_img_ori, -90)
    }[direction]


def move_kurir():
    global kurir_pos, current_path_index
    if current_path_index < len(path):
        kurir_pos = path[current_path_index]
        current_path_index += 1


def draw_buttons():
    pygame.draw.rect(screen, UI_COLOR, (0, 0, 190, current_height))
    pygame.draw.rect(screen, BUTTON_COLOR, (20, 20, 150, 40))
    draw_text("Load Peta", 40, 30, TEXT_COLOR)
    pygame.draw.rect(screen, BUTTON_COLOR, (20, 80, 150, 40))
    draw_text("Acak Posisi", 40, 90, TEXT_COLOR)
    pygame.draw.rect(screen, GREEN if not is_running else RED, (20, 140, 150, 40))
    draw_text("Mulai" if not is_running else "Berhenti", 40, 150, TEXT_COLOR)


def draw_text(text, x, y, color):
    screen.blit(font.render(text, True, color), (x, y))


def handle_click(pos):
    global is_running
    if 20 <= pos[0] <= 170:
        if 20 <= pos[1] <= 60:
            load_map()
        elif 70 <= pos[1] <= 110:
            acak_posisi()
        elif 120 <= pos[1] <= 160:
            is_running = not is_running

# Game loop
clock = pygame.time.Clock()
while True:
    screen.fill(UI_COLOR)
    if peta:
        screen.blit(peta, (0, 0))
    draw_buttons()
    if is_running and kurir_pos != tujuan_pos:
        move_kurir()
        if current_path_index >= len(path):
            is_running = False
    if kurir_pos and tujuan_pos:
        kurir_size = 30
        if is_safe_for_kurir(kurir_pos, kurir_size):
            scaled_kurir_pos = get_scaled_pos_centered(kurir_pos, kurir_size)
            rotated_kurir = pygame.transform.scale(rotate_kurir(get_kurir_direction()), (kurir_size, kurir_size))
            screen.blit(rotated_kurir, scaled_kurir_pos)
        pygame.draw.circle(screen, RED, get_scaled_pos(tujuan_pos), int(10 * current_width / 1500))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            handle_click(pygame.mouse.get_pos())
        elif event.type == pygame.VIDEORESIZE:
            current_width, current_height = event.size
            if original_peta:
                peta = pygame.transform.smoothscale(original_peta, (current_width, current_height))

    pygame.display.flip()
    clock.tick(60)
