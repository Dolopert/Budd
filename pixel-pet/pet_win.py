#!/usr/bin/env python3
"""
Pixel Pet — a pixel-art cat desktop companion for Windows.

Windows counterpart of pet.py (which targets macOS/PyObjC). Same behaviour:
walks across the bottom of the screen on top of all windows with true
per-pixel transparency, click-to-sit, drag-to-move, a right-click quit menu,
and speech bubbles.

Stack: Python 3.11 + PySide6 (Qt) + Pillow.  (Windows / cross-platform Qt.)
"""

import os
import random
import signal
import sys
import time

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QGuiApplication,
    QPixmap,
    QImage,
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QFont,
    QFontMetrics,
    QAction,
)
from PySide6.QtWidgets import QApplication, QWidget, QMenu
from PIL import Image

# ---------------------------------------------------------------------------
# Constants  (kept in sync with the macOS pet.py)
# ---------------------------------------------------------------------------
SIZE = 80
FPS = 30
ANIM_TICK_WALK = 6
ANIM_TICK_SIT = 15
SPEED = 2
SIT_DURATION = 3.0
WALK_PHRASE_INTERVAL = 8
BUBBLE_DURATION = 2.8
TAIL = 10  # speech-bubble tail height (px)

FACE_LEFT = True  # source sprites face left

SIT_PHRASES = ['~meow meow', 'purrr...', 'nya~', '(˘ω˘)']
WALK_PHRASES = ['where my fish nya', 'i am speed ~', 'sniff sniff', 'zoomies!!']


def resource_dir():
    """Folder that holds sprite_sheet/, working both in dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


WALK_SHEET = os.path.join(resource_dir(), "sprite_sheet", "walk_sprite.png")
SIT_SHEET = os.path.join(resource_dir(), "sprite_sheet", "sit_sprite.png")

try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS


# ---------------------------------------------------------------------------
# Sprite loading
# ---------------------------------------------------------------------------
def _remove_white_bg(img):
    """Flood-fill the exterior white background to transparency.

    Starting from the border keeps the cat's own cream/white body intact
    (interior whites are enclosed by the black outline, so the fill can't
    reach them).
    """
    from collections import deque

    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    seen = [[False] * h for _ in range(w)]
    q = deque()

    def is_white(p):
        return p[0] > 235 and p[1] > 235 and p[2] > 235

    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))

    while q:
        x, y = q.popleft()
        if seen[x][y]:
            continue
        seen[x][y] = True
        r, g, b, a = px[x, y]
        if not is_white((r, g, b)):
            continue
        px[x, y] = (r, g, b, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[nx][ny]:
                q.append((nx, ny))
    return img


def _pil_to_qpixmap(img):
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())  # copy() detaches from the temp buffer


def load_frames(sheet_path):
    """Slice a horizontal sheet into {1: right_frames, -1: left_frames}."""
    if not os.path.exists(sheet_path):
        print(f"Missing sprite sheet: {sheet_path}")
        print("Place the attached PNGs in the sprite_sheet/ folder.")
        sys.exit(1)

    sheet = Image.open(sheet_path).convert("RGBA")
    w, h = sheet.size
    n = max(1, round(w / h))
    fw = w / n

    originals, flipped = [], []
    for i in range(n):
        box = (int(round(i * fw)), 0, int(round((i + 1) * fw)), h)
        frame = sheet.crop(box).resize((SIZE, SIZE), RESAMPLE)
        frame = _remove_white_bg(frame)
        originals.append(_pil_to_qpixmap(frame))
        flipped.append(_pil_to_qpixmap(frame.transpose(Image.FLIP_LEFT_RIGHT)))

    if FACE_LEFT:
        return {1: flipped, -1: originals}
    return {1: originals, -1: flipped}


# ---------------------------------------------------------------------------
# Speech bubble window
# ---------------------------------------------------------------------------
class Bubble(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus,
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # clicks pass through
        self.message = ""
        self.font_ = QFont()
        self.font_.setPointSize(11)

    def set_text(self, msg):
        self.message = msg
        fm = QFontMetrics(self.font_)
        tw = fm.horizontalAdvance(msg)
        th = fm.height()
        w = max(60, tw + 32)
        h = th + 20 + TAIL
        self.resize(w, h)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Body: rounded rect.  Tail: separate triangle below the center.
        body = QRectF(1.0, 1.0, w - 2.0, h - TAIL - 2.0)
        path = QPainterPath()
        path.addRoundedRect(body, 9.0, 9.0)

        cx = w / 2.0
        tail = QPainterPath()
        tail.moveTo(cx - 8.0, h - TAIL - 1.0)
        tail.lineTo(cx + 8.0, h - TAIL - 1.0)
        tail.lineTo(cx, h - 1.0)
        tail.closeSubpath()

        shape = path.united(tail)  # union so the seam has no inner stroke
        p.setPen(QPen(QColor.fromRgbF(0.75, 0.75, 0.75), 1.5))
        p.setBrush(QColor(255, 255, 255))
        p.drawPath(shape)

        p.setPen(QColor(0, 0, 0))
        p.setFont(self.font_)
        p.drawText(body, Qt.AlignCenter, self.message)


# ---------------------------------------------------------------------------
# The cat
# ---------------------------------------------------------------------------
class Pet(QWidget):
    def __init__(self, app):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool,
        )
        self.app = app
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(SIZE, SIZE)

        self.walk = load_frames(WALK_SHEET)
        self.sit = load_frames(SIT_SHEET)
        self.bubble = Bubble()

        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.min_x = screen.left()
        self.max_x = screen.right() - SIZE + 1
        self.y = float(screen.bottom() - SIZE + 1)
        self.x = float(random.uniform(self.min_x, self.max_x))
        self.move(int(self.x), int(self.y))

        self.state = "walk"
        self.direction = random.choice((1, -1))
        self.frame_idx = 0
        self.anim_counter = 0
        self.sit_until = 0.0
        self.last_phrase = time.time()
        self.bubble_until = 0.0

        self._press_global = None
        self._press_pos = None
        self._moved = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(int(1000 / FPS))

    # --- painting ---
    def _current_pixmap(self):
        frames = (self.walk if self.state == "walk" else self.sit)[self.direction]
        return frames[self.frame_idx % len(frames)]

    def paintEvent(self, event):
        p = QPainter(self)
        p.drawPixmap(0, 0, self._current_pixmap())

    # --- main loop ---
    def tick(self):
        now = time.time()

        if self.state == "walk":
            self.x += SPEED * self.direction
            if self.x <= self.min_x:
                self.x = self.min_x
                self.direction = 1
            elif self.x >= self.max_x:
                self.x = self.max_x
                self.direction = -1
            self.move(int(self.x), int(self.y))

            self.anim_counter += 1
            if self.anim_counter >= ANIM_TICK_WALK:
                self.anim_counter = 0
                self.frame_idx = (self.frame_idx + 1) % len(self.walk[self.direction])

            if now - self.last_phrase >= WALK_PHRASE_INTERVAL:
                self.last_phrase = now
                self.say(random.choice(WALK_PHRASES))
        else:  # sit
            self.anim_counter += 1
            if self.anim_counter >= ANIM_TICK_SIT:
                self.anim_counter = 0
                self.frame_idx = (self.frame_idx + 1) % len(self.sit[self.direction])
            if now >= self.sit_until:
                self._start_walk()

        self.update()

        if self.bubble_until:
            if now >= self.bubble_until:
                self.bubble.hide()
                self.bubble_until = 0.0
            else:
                self._position_bubble()

    def _start_walk(self):
        self.state = "walk"
        self.frame_idx = 0
        self.anim_counter = 0
        self.last_phrase = time.time()

    # --- interaction ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_pos = self.pos()
            self._moved = False
        elif event.button() == Qt.RightButton:
            self._show_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._press_global is None:
            return
        delta = event.globalPosition().toPoint() - self._press_global
        if delta.manhattanLength() > 3:
            self._moved = True
        new = self._press_pos + delta
        self.move(new)
        self.x = float(new.x())
        self.y = float(new.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and not self._moved:
            self._sit()
        self._press_global = None

    def _sit(self):
        self.state = "sit"
        self.frame_idx = 0
        self.anim_counter = 0
        self.sit_until = time.time() + SIT_DURATION
        self.say(random.choice(SIT_PHRASES))

    def _show_menu(self, global_pos):
        menu = QMenu()
        quit_action = QAction("Quit Pixel Pet", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        menu.exec(global_pos)

    # --- speech bubbles ---
    def say(self, msg):
        self.bubble.set_text(msg)
        self._position_bubble()
        self.bubble.show()
        self.bubble.raise_()
        self.bubble_until = time.time() + BUBBLE_DURATION

    def _position_bubble(self):
        bw = self.bubble.width()
        bh = self.bubble.height()
        bx = int(self.x + SIZE / 2 - bw / 2)
        by = int(self.y - bh + 6)  # tail just above the cat's head
        self.bubble.move(bx, by)

    # --- quit ---
    def quit(self):
        self.timer.stop()
        self.bubble.hide()
        self.hide()
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # One instance only: a shared-memory handle that dies with the process.
    from PySide6.QtCore import QSharedMemory

    global _singleton
    _singleton = QSharedMemory("pixel_pet_singleton")
    if not _singleton.create(1):
        print("Pixel Pet is already running.")
        sys.exit(0)

    pet = Pet(app)
    pet.show()

    # Let Ctrl+C through: the FPS timer keeps returning to Python so the
    # signal handler can run.  A no-op timer guarantees it even when idle.
    signal.signal(signal.SIGINT, lambda *_: pet.quit())
    keepalive = QTimer()
    keepalive.start(200)
    keepalive.timeout.connect(lambda: None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
