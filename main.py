import pygame
import random
import math
import numpy as np
from pygame.locals import *
from tkinter import filedialog, Tk
from PIL import Image
from collections import deque
import heapq
import time

# Konstanta
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
JALAN_COLOR_RANGE = [(90, 90, 90), (150, 150, 150)]
PATH_MARGIN = 20
KURIR_SPEED = 4.0
ROAD_CENTER_OFFSET = 0.1

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Smart Kurir - Visualisasi Path")
font = pygame.font.SysFont("arial", 24)

# Variabel global
map_image = None
map_surface = None
road_mask = None
safe_road_mask = None
kurir_pos = (0.0, 0.0)
kurir_angle = 0
kurir_image = None
source_pos = None  # Diubah dari (0, 0) menjadi None
dest_pos = None    # Diubah dari (0, 0) menjadi None
highlight_path = []
info_lines = []
click_state = 0
path_to_follow = []
current_path_index = 0
moving = False
last_valid_pos = (0.0, 0.0)

def load_kurir_image():
    global kurir_image
    try:
        kurir_image = pygame.image.load("assets/segitiga_2.png")
        kurir_image = pygame.transform.scale(kurir_image, (30, 30))
    except:
        print("Gambar segitiga_2.png tidak ditemukan, menggunakan fallback")
        surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (0, 255, 0), [(15, 0), (0, 30), (30, 30)])
        kurir_image = surf

def is_road(image, pos):
    if image is None or pos is None:
        return False
        
    x, y = int(pos[0]), int(pos[1])
    if x < 0 or y < 0 or x >= image.width or y >= image.height:
        return False
    pixel = image.getpixel((x, y))
    return all(JALAN_COLOR_RANGE[0][i] <= pixel[i] <= JALAN_COLOR_RANGE[1][i] for i in range(3))

def create_road_masks(image):
    """Membuat mask jalan dan mask area aman dengan margin"""
    global road_mask, safe_road_mask
    if image is None:
        return
        
    width, height = image.size
    road_mask = np.zeros((height, width), dtype=bool)
    safe_road_mask = np.zeros((height, width), dtype=bool)
    
    # Buat mask dasar untuk jalan
    for y in range(height):
        for x in range(width):
            road_mask[y, x] = is_road(image, (x, y))
    
    # Buat mask area aman dengan margin
    for y in range(PATH_MARGIN, height - PATH_MARGIN):
        for x in range(PATH_MARGIN, width - PATH_MARGIN):
            if not road_mask[y, x]:
                continue
                
            # Periksa area sekitar dengan margin PATH_MARGIN
            safe = True
            for dy in range(-PATH_MARGIN, PATH_MARGIN + 1):
                for dx in range(-PATH_MARGIN, PATH_MARGIN + 1):
                    if not road_mask[y + dy, x + dx]:
                        safe = False
                        break
                if not safe:
                    break
            safe_road_mask[y, x] = safe

def is_safe_road_position(pos):
    """Cek apakah posisi aman dengan margin"""
    global safe_road_mask
    if pos is None or safe_road_mask is None:  # Tambah pengecekan None
        return False
    
    try:
        x, y = int(round(pos[0])), int(round(pos[1]))
        if x < 0 or y < 0 or x >= safe_road_mask.shape[1] or y >= safe_road_mask.shape[0]:
            return False
        return safe_road_mask[y, x]
    except:
        return False

def find_road_center(start_pos):
    """Temukan posisi jalan yang aman dengan margin"""
    global safe_road_mask
    if start_pos is None or safe_road_mask is None:
        return start_pos
    
    try:
        x, y = int(round(start_pos[0])), int(round(start_pos[1]))
        max_radius = min(15, safe_road_mask.shape[0]//2, safe_road_mask.shape[1]//2)
        
        # Coba posisi tepat dulu
        if (0 <= y < safe_road_mask.shape[0] and 
            0 <= x < safe_road_mask.shape[1] and 
            safe_road_mask[y, x]):
            return (float(x) + ROAD_CENTER_OFFSET, float(y) + ROAD_CENTER_OFFSET)
        
        # Pencarian spiral untuk posisi aman terdekat
        for radius in range(1, max_radius + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = x + dx, y + dy
                        if (0 <= ny < safe_road_mask.shape[0] and 
                            0 <= nx < safe_road_mask.shape[1] and 
                            safe_road_mask[ny, nx]):
                            return (float(nx) + ROAD_CENTER_OFFSET, float(ny) + ROAD_CENTER_OFFSET)
    except Exception as e:
        print(f"Error in find_road_center: {e}")
    
    return start_pos

def random_road_position():
    """Hasilkan posisi acak di jalan yang aman"""
    global safe_road_mask
    if safe_road_mask is None:
        return None  # Kembalikan None bukan (0, 0)
    
    try:
        safe_positions = np.argwhere(safe_road_mask)
        if len(safe_positions) == 0:
            return None
            
        idx = np.random.randint(len(safe_positions))
        y, x = safe_positions[idx]
        return (float(x) + ROAD_CENTER_OFFSET, float(y) + ROAD_CENTER_OFFSET)
    except:
        return None

def calculate_angle(current, target):
    if current is None or target is None:
        return 0
        
    dx = target[0] - current[0]
    dy = target[1] - current[1]
    return math.degrees(math.atan2(dy, dx))

def smooth_path(path):
    if path is None or len(path) < 3:
        return path if path else []
    
    smoothed = [path[0]]
    for i in range(1, len(path)-1):
        prev = smoothed[-1]
        next = path[i+1]
        if (prev[0] == path[i][0] == next[0]) or (prev[1] == path[i][1] == next[1]):
            continue
        smoothed.append(path[i])
    smoothed.append(path[-1])
    return smoothed

def bfs(start, goal):
    global safe_road_mask
    if safe_road_mask is None or start is None or goal is None:
        return None
        
    queue = deque()
    queue.append((start, [start]))
    visited = set()
    visited.add(start)
    
    # 8 arah pergerakan termasuk diagonal
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0),
                 (-1, -1), (-1, 1), (1, -1), (1, 1)]
    
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
            
        for dx, dy in directions:
            nx, ny = current[0] + dx, current[1] + dy
            if (0 <= ny < safe_road_mask.shape[0] and 
                0 <= nx < safe_road_mask.shape[1] and 
                safe_road_mask[ny, nx] and 
                (nx, ny) not in visited):
                queue.append(((nx, ny), path + [(nx, ny)]))
                visited.add((nx, ny))
    return None

def heuristic(a, b):
    if a is None or b is None:
        return float('inf')
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(start, goal):
    global safe_road_mask
    if safe_road_mask is None or start is None or goal is None:
        return None
        
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    
    # 8 arah pergerakan
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0),
                 (-1, -1), (-1, 1), (1, -1), (1, 1)]
    
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
            
            if not (0 <= neighbor[1] < safe_road_mask.shape[0] and 
                    0 <= neighbor[0] < safe_road_mask.shape[1] and 
                    safe_road_mask[neighbor[1], neighbor[0]]):
                continue
                
            move_cost = 1.4 if dx != 0 and dy != 0 else 1.0
            tentative_g = g_score[current] + move_cost
            
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))
    return None

class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
    
    def draw(self, surface):
        pygame.draw.rect(surface, (180, 180, 180), self.rect)
        label = font.render(self.text, True, (0, 0, 0))
        surface.blit(label, (self.rect.x + 5, self.rect.y + 5))
    
    def click(self, pos):
        if self.rect.collidepoint(pos):
            try:
                self.callback()
            except Exception as e:
                print(f"Error in button callback: {e}")
                info_lines.append(f"[ERROR] Button error: {str(e)}")

def draw_kurir(pos, angle):
    if pos is None or kurir_image is None:
        return
        
    try:
        rotated_image = pygame.transform.rotate(kurir_image, -angle)
        new_rect = rotated_image.get_rect(center=(200 + pos[0], pos[1]))
        screen.blit(rotated_image, new_rect.topleft)
    except:
        pass

def draw_info():
    if info_lines is None:
        return
        
    info_box_height = 30
    for i, line in enumerate(info_lines):
        try:
            y_pos = SCREEN_HEIGHT - (len(info_lines) - i) * info_box_height
            pygame.draw.rect(screen, (240, 240, 240), (10, y_pos, 180, info_box_height))
            pygame.draw.rect(screen, (150, 150, 150), (10, y_pos, 180, info_box_height), 2)
            label = font.render(line, True, (0, 0, 0))
            screen.blit(label, (15, y_pos + 5))
        except:
            pass

def render():
    try:
        screen.fill((200, 200, 200))
        for btn in buttons:
            btn.draw(screen)
            
        if map_surface:
            screen.blit(map_surface, (200, 0))
            
            # Visualisasi path
            if highlight_path:
                for i, pos in enumerate(highlight_path):
                    if pos is None:
                        continue
                        
                    try:
                        color = (255 - i * 255 // len(highlight_path), 
                                i * 255 // len(highlight_path), 0)
                        pygame.draw.circle(screen, color, (200 + int(pos[0]), int(pos[1])), 3)
                        
                        if i < len(highlight_path) - 1 and highlight_path[i+1] is not None:
                            next_pos = highlight_path[i+1]
                            pygame.draw.line(screen, color, 
                                           (200 + int(pos[0]), int(pos[1])),
                                           (200 + int(next_pos[0]), int(next_pos[1])), 2)
                    except:
                        continue
            
            # Titik awal dan tujuan
            if source_pos is not None:
                pygame.draw.circle(screen, (255, 255, 0), (200 + int(source_pos[0]), int(source_pos[1])), 8)
            if dest_pos is not None:
                pygame.draw.circle(screen, (255, 0, 0), (200 + int(dest_pos[0]), int(dest_pos[1])), 8)
            
            # Kurir
            if kurir_pos != (0, 0):
                draw_kurir(kurir_pos, kurir_angle)
        
        draw_info()
        pygame.display.flip()
    except Exception as e:
        print(f"Render error: {e}")

def load_map():
    global map_image, map_surface, road_mask, safe_road_mask
    try:
        Tk().withdraw()
        file_path = filedialog.askopenfilename()
        if file_path:
            info_lines.append("[INFO] Memuat peta...")
            render()
            
            map_image = Image.open(file_path).convert('RGB')
            map_image = map_image.resize((SCREEN_WIDTH - 200, SCREEN_HEIGHT))
            map_surface = pygame.image.fromstring(map_image.tobytes(), map_image.size, map_image.mode)
            
            info_lines.append("[INFO] Membuat road mask...")
            render()
            create_road_masks(map_image)
            info_lines.append(f"[INFO] Peta dimuat. Area aman: {np.sum(safe_road_mask)} piksel")
    except Exception as e:
        info_lines.append(f"[ERROR] Gagal memuat peta: {str(e)}")

def random_kurir():
    global kurir_pos, kurir_angle, last_valid_pos
    try:
        pos = random_road_position()
        if pos is not None:
            kurir_pos = pos
            last_valid_pos = kurir_pos
            kurir_angle = 0
            info_lines.append("[INFO] Posisi kurir diacak")
        else:
            info_lines.append("[ERROR] Tidak ada posisi aman untuk kurir!")
    except Exception as e:
        info_lines.append(f"[ERROR] Gagal mengacak posisi kurir: {str(e)}")

def random_flag():
    global source_pos, dest_pos
    try:
        source_pos = random_road_position()
        dest_pos = random_road_position()
        
        if source_pos is not None and dest_pos is not None:
            info_lines.append("[INFO] Posisi tujuan diacak")
        else:
            info_lines.append("[ERROR] Gagal mengacak posisi tujuan")
    except Exception as e:
        info_lines.append(f"[ERROR] Gagal mengacak posisi: {str(e)}")

def move_kurir():
    global kurir_pos, current_path_index, moving, path_to_follow, kurir_angle, last_valid_pos
    
    if not moving or current_path_index >= len(path_to_follow) - 1:
        moving = False
        return
    
    try:
        target_pos = path_to_follow[current_path_index + 1]
        if target_pos is None:
            moving = False
            return
            
        dx = target_pos[0] - kurir_pos[0]
        dy = target_pos[1] - kurir_pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        kurir_angle = calculate_angle(kurir_pos, target_pos)
        
        if distance > KURIR_SPEED:
            dx /= distance
            dy /= distance
            new_pos = (kurir_pos[0] + dx * KURIR_SPEED, 
                      kurir_pos[1] + dy * KURIR_SPEED)
            
            if is_safe_road_position(new_pos):
                kurir_pos = new_pos
                last_valid_pos = new_pos
            else:
                kurir_pos = last_valid_pos
        else:
            kurir_pos = target_pos
            current_path_index += 1
            
            if current_path_index >= len(path_to_follow) - 1:
                moving = False
                info_lines.append("[SELESAI] Paket terkirim!")
    except Exception as e:
        moving = False
        info_lines.append(f"[ERROR] Gagal memindahkan kurir: {str(e)}")

def mulai():
    global path_to_follow, current_path_index, moving, info_lines, kurir_pos, last_valid_pos, highlight_path, source_pos, dest_pos
    
    try:
        # Validasi awal
        if map_image is None:
            info_lines = ["[ERROR] Peta belum dimuat!"]
            return
        
        if source_pos is None or not is_safe_road_position(source_pos):
            info_lines = ["[ERROR] Posisi sumber belum ditentukan atau tidak valid!"]
            return
            
        if dest_pos is None or not is_safe_road_position(dest_pos):
            info_lines = ["[ERROR] Posisi tujuan belum ditentukan atau tidak valid!"]
            return
            
        if kurir_pos is None or not is_safe_road_position(kurir_pos):
            info_lines = ["[ERROR] Posisi kurir belum ditentukan atau tidak valid!"]
            return
        
        info_lines = ["[INFO] Memulai perhitungan jalur..."]
        render()
        pygame.time.delay(100)  # Beri waktu untuk update tampilan

        # Pastikan posisi valid
        kurir_pos = find_road_center(kurir_pos)
        source_pos = find_road_center(source_pos)
        dest_pos = find_road_center(dest_pos)
        last_valid_pos = kurir_pos

        # Hitung jalur ke sumber
        t1 = time.time()
        start_point = (int(kurir_pos[0]), int(kurir_pos[1]))
        mid_point = (int(source_pos[0]), int(source_pos[1]))
        path1 = bfs(start_point, mid_point)
        t2 = time.time()

        if not path1:
            info_lines = ["[ERROR] Tidak ada jalur ke sumber!"]
            return

        # Hitung jalur ke tujuan
        t3 = time.time()
        end_point = (int(dest_pos[0]), int(dest_pos[1]))
        path2 = astar(mid_point, end_point)
        t4 = time.time()

        if not path2:
            info_lines = ["[ERROR] Tidak ada jalur ke tujuan!"]
            return

        # Gabungkan path
        full_path = smooth_path(path1 + path2[1:])
        path_to_follow = [(float(x) + ROAD_CENTER_OFFSET, float(y) + ROAD_CENTER_OFFSET) for (x, y) in full_path]
        highlight_path = path_to_follow.copy()

        info_lines = [
            f"[INFO] Perhitungan selesai",
            f"BFS: {t2-t1:.3f} detik ({len(path1)} langkah)",
            f"A*: {t4-t3:.3f} detik ({len(path2)} langkah)",
            f"Total: {len(full_path)} langkah"
        ]
        
        current_path_index = 0
        moving = True

    except Exception as e:
        info_lines = [
            "[ERROR] Terjadi kesalahan saat menghitung jalur:",
            str(e)
        ]

def reset_simulasi():
    global kurir_pos, kurir_angle, source_pos, dest_pos, info_lines, click_state
    global path_to_follow, current_path_index, moving, last_valid_pos, highlight_path
    
    try:
        kurir_pos = (0.0, 0.0)
        kurir_angle = 0
        source_pos = None  # Reset ke None
        dest_pos = None    # Reset ke None
        info_lines = ["[INFO] Simulasi telah di-reset."]
        click_state = 0
        path_to_follow = []
        current_path_index = 0
        moving = False
        last_valid_pos = (0.0, 0.0)
        highlight_path = []
    except Exception as e:
        info_lines = [f"[ERROR] Gagal mereset simulasi: {str(e)}"]

# Load gambar kurir
load_kurir_image()

# Daftar tombol
buttons = [
    Button(10, 10, 150, 40, "Load Peta", load_map),
    Button(10, 60, 150, 40, "Acak Kurir", random_kurir),
    Button(10, 110, 150, 40, "Acak Tujuan", random_flag),
    Button(10, 160, 150, 40, "Mulai", mulai),
    Button(10, 210, 150, 40, "Reset", reset_simulasi)
]

# Main loop
running = True
clock = pygame.time.Clock()

while running:
    try:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                for btn in buttons:
                    btn.click(event.pos)
                
                if event.pos[0] > 200 and map_image:
                    mx, my = event.pos[0] - 200, event.pos[1]
                    if is_safe_road_position((mx, my)):
                        pos = find_road_center((mx, my))
                        if pos is None:
                            continue
                            
                        if click_state == 0:
                            kurir_pos = pos
                            info_lines = ["[INFO] Posisi kurir dipilih."]
                        elif click_state == 1:
                            source_pos = pos
                            info_lines = ["[INFO] Titik awal dipilih."]
                        elif click_state == 2:
                            dest_pos = pos
                            info_lines = ["[INFO] Titik tujuan dipilih."]
                        click_state = (click_state + 1) % 3
                    else:
                        info_lines = ["[WARNING] Posisi terlalu dekat dengan non-jalan atau tidak aman!"]
        
        if moving:
            move_kurir()
        
        render()
        clock.tick(60)
    except Exception as e:
        print(f"Error in main loop: {e}")
        running = False

pygame.quit()
