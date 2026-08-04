import pygame
import sys
import serial
import threading
from datetime import datetime
import json
import os

# -------------------
# CONFIG
# -------------------
SERIAL_PORT = "/dev/ttyACM0"  # CHANGE THIS
BAUD = 115200

pygame.init()

FULLSCREEN = False

def set_fullscreen(enabled):
    global screen
    global WIDTH
    global HEIGHT
    global FULLSCREEN

    FULLSCREEN = enabled

    if FULLSCREEN:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((1024, 600))

    WIDTH, HEIGHT = screen.get_size()

#WIDTH, HEIGHT = 1024, 600
#screen = pygame.display.set_mode((WIDTH, HEIGHT))

pygame.display.set_caption("Chore Chart")

set_fullscreen(False)

clock = pygame.time.Clock()

font = pygame.font.SysFont("courier", 26)
small_font = pygame.font.SysFont("courier", 20)
month_font = pygame.font.Font("Fonts/Cafe24Ssurround-v2.0.ttf", 70)
day_font = pygame.font.Font("Fonts/Cafe24Ssurround-v2.0.ttf", 140)

# -------------------
# DATA STRUCTURE (DAY-BASED)
# -------------------
person_keys = {
    "Person 1" : "Y",
    "Person 2" : "M",
    "Person 3" : "E"
}

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

layout = [
    ["Monday", "Tuesday", "Wednesday", "Thursday"],
    ["Friday", "Saturday", "Sunday", None]
]

backgrounds = {
    "Monday": pygame.image.load("Background/UI Design 1.jpeg"),
    "Tuesday": pygame.image.load("Background/UI Design 2.jpeg"),
    "Wednesday": pygame.image.load("Background/UI Design 3.jpeg"),
    "Thursday": pygame.image.load("Background/UI Design 4.jpeg"),
    "Friday": pygame.image.load("Background/UI Design 5.jpeg"),
    "Saturday": pygame.image.load("Background/UI Design 6.jpeg"),
    "Sunday": pygame.image.load("Background/UI Design 7.jpeg"),
}

STATE_FILE = "state.json"

chores = {}
day_skip = 0
people = []

START_X = 28
START_Y = 55

DAY_SPACING_X = 190
ROW_SPACING_Y = 230

PERSON_ROW_Y = 25

days_order = list(chores.keys())

# -------------------
# FUNCTIONS
# -------------------
def load_state():

    global chores
    global day_skip
    global people

    try:

        if not os.path.exists(STATE_FILE):
            return

        if os.path.getsize(STATE_FILE) == 0:
            return

        with open(STATE_FILE, "r") as f:
            data = json.load(f)

        chores = data.get("schedule", {})
        people = data.get("people", [])

        saved_date = data.get("last_date")
        current_date = datetime.now().strftime("%Y-%m-%d")

        # if a new day has started
        if saved_date != current_date:

            # reset skip amount
            day_skip = 0

            # update stored date
            data["last_date"] = current_date
            data["day_skip"] = 0

            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=4)

        else:
            day_skip = data.get("day_skip", 0)

    except json.JSONDecodeError:
        pass

    except Exception as e:
        print("Load error:", e)

def get_today():
    # Returns: "Monday", "Tuesday", ...
    return datetime.now().strftime("%A")

def get_today_index():
    return DAYS.index(get_today())

def get_active_day():
    today_idx = get_today_index()
    active_idx = (today_idx + day_skip) % 7
    return DAYS[active_idx]

def draw_background():
    screen.blit(backgrounds[get_active_day()], (0, 0))

def draw():
    canvas = pygame.Surface((WIDTH, HEIGHT))
    canvas.blit(backgrounds[get_active_day()], (0, 0))

    start_x = 28
    start_y = 55

    cols = 4
    cell_w = (WIDTH - 10) // cols
    cell_h = 290

    for r, row in enumerate(layout):
        for c, day in enumerate(row):

            if day is None:
                continue

            x = start_x + c * cell_w
            y = start_y + r * cell_h

            # draw chores inside each cell
            for row_index, person in enumerate(people):

                py = y + 50 + row_index * 50
                px = x + 10

                day_entries = chores.get(day, [])

                for chore in day_entries:

                    if chore["name"] != person:
                        continue

                    text = person + ": " + chore["chore"]

                    surface = small_font.render(text, True, (0, 0, 0))

                    canvas.blit(surface, (px, py))

                    if chore.get("completed"):

                        pygame.draw.line(
                            canvas,
                            (0, 0, 0),
                            (px, py + 10),
                            (px + surface.get_width(), py + 10),
                            2
                        )

                    py += 20
        # bottom-right cell position
        # -------------------
    # DATE DISPLAY (BOTTOM RIGHT CELL)
    # -------------------
    now = datetime.now()
    current_month = now.strftime("%b").upper()
    current_day = str(now.day)

    month_surface = month_font.render(current_month, True, (255, 255, 255))
    day_surface = day_font.render(current_day, True, (51, 76, 106))

    center_point_month = (895, 360)
    center_point_day = (895, 490)

    rect_month = month_surface.get_rect(center=center_point_month)
    rect_day = day_surface.get_rect(center=center_point_day)

    canvas.blit(month_surface, rect_month)
    canvas.blit(day_surface, rect_day)

    # -------------------
    # ROTATE ENTIRE SCREEN 180°
    # -------------------

    rotated = pygame.transform.rotate(canvas, 180)

    screen.blit(rotated, (0, 0))

    pygame.display.flip()
# -------------------
# MAIN LOOP
# -------------------
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        # ESC key exits fullscreen
        if event.type == pygame.KEYDOWN:

            # Q quits pygame
            if event.key == pygame.K_q:
                pygame.quit()
                sys.exit()

            # ESC exits fullscreen
            if event.key == pygame.K_ESCAPE:
                set_fullscreen(False)

            # F enters fullscreen
            if event.key == pygame.K_f:
                set_fullscreen(True)

    load_state()
    draw()
    clock.tick(30)
