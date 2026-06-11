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
from PIL import Image, ImageOps, ImageDraw

# ---------------------------------------------------------------------------
# Constants  (kept in sync with the macOS pet.py)
# ---------------------------------------------------------------------------
SIZE = 80
FPS = 30
ANIM_TICK_WALK = 6
ANIM_TICK_SIT = 15
SPEED = 2
SIT_DURATION = 3.0
AUTO_SIT_MIN = 8.0   # the cat sits on its own after walking this long...
AUTO_SIT_MAX = 20.0  # ...up to this long (a random gap in between)
WALK_PHRASE_INTERVAL = 8
BUBBLE_DURATION = 2.8
TAIL = 10  # speech-bubble tail height (px)

FACE_LEFT = False  # source sprites face right

SIT_PHRASES = ['~meow meow', 'purrr...', 'nya~', '(˘ω˘)']
WALK_PHRASES = ['love ai ouan', 'yak kin khanom ~', 'ai ouan na rak tee sood', 'ouannnnnn!!']


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
    """Make the exterior white background transparent.

    Flood-fills inward from the four corners using Pillow's C flood-fill, so
    the cat's own cream/white body stays intact (those interior pixels are
    enclosed by the black outline and never reached from the border).
    """
    img = img.convert("RGBA")
    w, h = img.size
    rgb = img.convert("RGB")
    mark = (255, 0, 255)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(rgb, seed, mark, thresh=40)
    src = rgb.load()
    dst = img.load()
    for y in range(h):
        for x in range(w):
            if src[x, y] == mark:
                r, g, b, _ = dst[x, y]
                dst[x, y] = (r, g, b, 0)
    return img


def _column_spans(sheet):
    """Find the x-ranges of each sprite by detecting gaps of blank columns."""
    w, h = sheet.size
    px = sheet.load()
    step = max(1, h // 200)
    spans, start = [], None
    for x in range(w):
        content = False
        for y in range(0, h, step):
            r, g, b, a = px[x, y]
            if a > 10 and not (r > 235 and g > 235 and b > 235):
                content = True
                break
        if content and start is None:
            start = x
        elif not content and start is not None:
            spans.append((start, x))
            start = None
    if start is not None:
        spans.append((start, w))
    return [(a, b) for a, b in spans if (b - a) > w * 0.02]


def _pil_to_qpixmap(img):
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())  # copy() detaches from the temp buffer


def load_frames(sheet_path):
    """Slice a horizontal sheet into {1: right_frames, -1: left_frames}.

    Frames are detected by the blank columns between cats (robust to padding),
    background-removed, then scaled by one shared factor and bottom-aligned so
    the cat's feet stay on a steady baseline across frames.
    """
    if not os.path.exists(sheet_path):
        print(f"Missing sprite sheet: {sheet_path}")
        print("Place the attached PNGs in the sprite_sheet/ folder.")
        sys.exit(1)

    sheet = Image.open(sheet_path).convert("RGBA")
    spans = _column_spans(sheet) or [(0, sheet.size[0])]
    h = sheet.size[1]

    tiles = []
    for x0, x1 in spans:
        tile = sheet.crop((x0, 0, x1, h))
        tile = ImageOps.expand(tile, border=6, fill=(255, 255, 255, 255))
        longest = max(tile.size)
        if longest > 300:  # pre-shrink so the flood fill is fast
            k = 300.0 / longest
            tile = tile.resize(
                (max(1, int(tile.size[0] * k)), max(1, int(tile.size[1] * k))),
                RESAMPLE,
            )
        tile = _remove_white_bg(tile)
        bbox = tile.getbbox()
        if bbox:
            tile = tile.crop(bbox)
        tiles.append(tile)

    scale = (SIZE * 0.92) / max(max(t.size) for t in tiles)
    originals, flipped = [], []
    for t in tiles:
        nw = max(1, int(round(t.size[0] * scale)))
        nh = max(1, int(round(t.size[1] * scale)))
        sprite = t.resize((nw, nh), RESAMPLE)
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(sprite, ((SIZE - nw) // 2, SIZE - nh), sprite)  # bottom-align
        originals.append(_pil_to_qpixmap(canvas))
        flipped.append(_pil_to_qpixmap(canvas.transpose(Image.FLIP_LEFT_RIGHT)))

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
        self._schedule_auto_sit()

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

            if now >= self.auto_sit_at:
                self._sit()
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

    def _schedule_auto_sit(self):
        """Pick the next moment the cat will sit down by itself."""
        self.auto_sit_at = time.time() + random.uniform(AUTO_SIT_MIN, AUTO_SIT_MAX)

    def _start_walk(self):
        self.state = "walk"
        self.frame_idx = 0
        self.anim_counter = 0
        self.last_phrase = time.time()
        self._schedule_auto_sit()

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
