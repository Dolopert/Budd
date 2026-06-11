#!/usr/bin/env python3.11
"""
Pixel Pet — a pixel-art cat desktop companion for macOS.

Walks across the bottom of the screen on top of all windows, with true
per-pixel transparency, click-to-sit, drag-to-move, a right-click quit menu,
and speech bubbles.

Stack: Python 3.11 + PyObjC/Cocoa + Pillow.  (macOS only.)
"""

import io
import os
import random
import signal
import sys
import time

import objc
from Foundation import (
    NSObject,
    NSData,
    NSMakeRect,
    NSMakePoint,
    NSMakeSize,
    NSString,
    NSZeroRect,
)
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSWindow,
    NSWindowStyleMaskBorderless,
    NSBackingStoreBuffered,
    NSColor,
    NSView,
    NSImage,
    NSBezierPath,
    NSMenu,
    NSMenuItem,
    NSTimer,
    NSScreen,
    NSEvent,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSCompositingOperationSourceOver,
)
from PIL import Image, ImageOps, ImageDraw

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SIZE = 80                 # on-screen size of the cat (px)
FPS = 30                  # frames per second of the main loop
ANIM_TICK_WALK = 6        # advance walk frame every N ticks
ANIM_TICK_SIT = 15        # advance sit frame every N ticks
SPEED = 2                 # horizontal pixels moved per tick while walking
SIT_DURATION = 3.0        # seconds the cat sits after a click
AUTO_SIT_MIN = 8.0        # the cat sits on its own after walking this long...
AUTO_SIT_MAX = 20.0       # ...up to this long (a random gap in between)
WALK_PHRASE_INTERVAL = 8  # seconds between spontaneous walking phrases
BUBBLE_DURATION = 2.8     # seconds a speech bubble stays up
WINDOW_LEVEL = 25         # above apps, below system UI
TAIL = 10                 # height of the speech-bubble tail (px)

# The source sprites face RIGHT.  Flip the originals to produce left frames.
FACE_LEFT = False

SIT_PHRASES = ['~meow meow', 'purrr...', 'nya~', '(˘ω˘)']
WALK_PHRASES = ['love ai ouan', 'yak kin khanom ~', 'ai ouan na rak tee sood', 'ouannnnnn!!']

LOCK_PATH = "/tmp/pixel_pet.lock"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WALK_SHEET = os.path.join(BASE_DIR, "sprite_sheet", "walk_sprite.png")
SIT_SHEET = os.path.join(BASE_DIR, "sprite_sheet", "sit_sprite.png")

try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9.1
    RESAMPLE = Image.LANCZOS


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------
_lock_handle = None


def acquire_lock():
    """Refuse to start a second copy using a flock on /tmp/pixel_pet.lock."""
    global _lock_handle
    try:
        import fcntl
    except ImportError:
        return  # non-POSIX; skip the lock
    _lock_handle = open(LOCK_PATH, "w")
    try:
        fcntl.flock(_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Pixel Pet is already running.")
        sys.exit(0)
    _lock_handle.write(str(os.getpid()))
    _lock_handle.flush()


def release_lock():
    global _lock_handle
    try:
        if _lock_handle is not None:
            _lock_handle.close()
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except OSError:
        pass


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


def _pil_to_nsimage(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw = buf.getvalue()
    data = NSData.dataWithBytes_length_(raw, len(raw))
    return NSImage.alloc().initWithData_(data)


def load_frames(sheet_path):
    """Slice a horizontal sprite sheet into {1: right_frames, -1: left_frames}.

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
        originals.append(_pil_to_nsimage(canvas))
        flipped.append(_pil_to_nsimage(canvas.transpose(Image.FLIP_LEFT_RIGHT)))

    if FACE_LEFT:
        return {1: flipped, -1: originals}
    return {1: originals, -1: flipped}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------
class PetView(NSView):
    """Draws the current cat frame and routes mouse events to the controller."""

    def initWithFrame_(self, frame):
        self = objc.super(PetView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.image = None
        self.controller = None
        self._down = None
        self._origin = None
        self._dragged = False
        return self

    def isFlipped(self):
        return False

    def acceptsFirstMouse_(self, event):
        return True

    def drawRect_(self, rect):
        if self.image is not None:
            self.image.drawInRect_fromRect_operation_fraction_(
                self.bounds(), NSZeroRect, NSCompositingOperationSourceOver, 1.0
            )

    # --- mouse: drag to move, click (no drag) to sit ---
    def mouseDown_(self, event):
        self._down = NSEvent.mouseLocation()
        self._origin = self.window().frame().origin
        self._dragged = False

    def mouseDragged_(self, event):
        if self._down is None:
            return
        self._dragged = True
        cur = NSEvent.mouseLocation()
        new = NSMakePoint(
            self._origin.x + (cur.x - self._down.x),
            self._origin.y + (cur.y - self._down.y),
        )
        self.window().setFrameOrigin_(new)
        if self.controller is not None:
            self.controller.on_drag(new)

    def mouseUp_(self, event):
        if not self._dragged and self.controller is not None:
            self.controller.on_click()
        self._down = None

    def rightMouseDown_(self, event):
        menu = NSMenu.alloc().init()
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Pixel Pet", b"quitApp:", ""
        )
        item.setTarget_(self.controller)
        menu.addItem_(item)
        NSMenu.popUpContextMenu_withEvent_forView_(menu, event, self)


class BubbleView(NSView):
    """A rounded speech bubble with a downward tail and centered text."""

    def initWithFrame_(self, frame):
        self = objc.super(BubbleView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.message = ""
        self.attrs = None
        return self

    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        b = self.bounds()
        w, h = b.size.width, b.size.height
        stroke = NSColor.colorWithWhite_alpha_(0.75, 1.0)

        # Bubble body — rounded rect, NOT hand-built arcs.
        body = NSMakeRect(1.0, TAIL, w - 2.0, h - TAIL - 1.0)
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(body, 9.0, 9.0)
        NSColor.whiteColor().setFill()
        path.fill()
        stroke.setStroke()
        path.setLineWidth_(1.5)
        path.stroke()

        # Tail — a separate triangle below the body center.
        cx = w / 2.0
        tail = NSBezierPath.bezierPath()
        tail.moveToPoint_(NSMakePoint(cx - 8.0, TAIL + 0.5))
        tail.lineToPoint_(NSMakePoint(cx + 8.0, TAIL + 0.5))
        tail.lineToPoint_(NSMakePoint(cx, 0.5))
        tail.closePath()
        NSColor.whiteColor().setFill()
        tail.fill()
        stroke.setStroke()
        tail.setLineWidth_(1.5)
        tail.stroke()

        if self.message and self.attrs is not None:
            s = NSString.stringWithString_(self.message)
            tsize = s.sizeWithAttributes_(self.attrs)
            tx = (w - tsize.width) / 2.0
            ty = TAIL + ((h - TAIL) - tsize.height) / 2.0
            s.drawAtPoint_withAttributes_(NSMakePoint(tx, ty), self.attrs)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------
class PetController(NSObject):

    def init(self):
        self = objc.super(PetController, self).init()
        if self is None:
            return None
        self.walk = None
        self.sit = None
        self.pet_window = None
        self.pet_view = None
        self.bubble_window = None
        self.bubble_view = None
        self.timer = None

        self.state = "walk"
        self.direction = 1
        self.frame_idx = 0
        self.anim_counter = 0
        self.sit_until = 0.0
        self.last_phrase = time.time()
        self._schedule_auto_sit()
        self.bubble_until = 0.0
        self.x = 0.0
        self.y = 0.0
        self.max_x = 0.0
        return self

    # --- setup ---
    def setup(self):
        self.walk = load_frames(WALK_SHEET)
        self.sit = load_frames(SIT_SHEET)

        screen = NSScreen.mainScreen().visibleFrame()
        self.x = random.uniform(0, max(1.0, screen.size.width - SIZE))
        self.y = screen.origin.y
        self.max_x = screen.origin.x + screen.size.width - SIZE
        self.direction = random.choice((1, -1))

        self.pet_window = self._make_window(SIZE, SIZE, mouse=True)
        self.pet_view = PetView.alloc().initWithFrame_(NSMakeRect(0, 0, SIZE, SIZE))
        self.pet_view.controller = self
        self.pet_window.setContentView_(self.pet_view)
        self.pet_window.setFrameOrigin_(NSMakePoint(self.x, self.y))
        self.pet_window.orderFront_(None)

        self.bubble_window = self._make_window(80, 40, mouse=False)
        self.bubble_view = BubbleView.alloc().initWithFrame_(NSMakeRect(0, 0, 80, 40))
        self.bubble_window.setContentView_(self.bubble_view)

        self._update_image()

        self.timer = (
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                1.0 / FPS, self, b"tick:", None, True
            )
        )

    def _make_window(self, w, h, mouse):
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, w, h),
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setLevel_(WINDOW_LEVEL)
        win.setHasShadow_(False)
        win.setIgnoresMouseEvents_(not mouse)
        return win

    # --- main loop ---
    def tick_(self, timer):
        now = time.time()

        if self.state == "walk":
            self.x += SPEED * self.direction
            if self.x <= 0:
                self.x = 0
                self.direction = 1
            elif self.x >= self.max_x:
                self.x = self.max_x
                self.direction = -1
            self.pet_window.setFrameOrigin_(NSMakePoint(self.x, self.y))

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

        self._update_image()

        if self.bubble_until:
            if now >= self.bubble_until:
                self.bubble_window.orderOut_(None)
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

    def _update_image(self):
        frames = (self.walk if self.state == "walk" else self.sit)[self.direction]
        idx = self.frame_idx % len(frames)
        self.pet_view.image = frames[idx]
        self.pet_view.setNeedsDisplay_(True)

    # --- interaction ---
    def _sit(self):
        self.state = "sit"
        self.frame_idx = 0
        self.anim_counter = 0
        self.sit_until = time.time() + SIT_DURATION
        self.say(random.choice(SIT_PHRASES))

    def on_click(self):
        self._sit()

    def on_drag(self, point):
        self.x = float(point.x)
        self.y = float(point.y)

    # --- speech bubbles ---
    def say(self, msg):
        font = NSFont.systemFontOfSize_(13.0)
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: NSColor.blackColor(),
        }
        s = NSString.stringWithString_(msg)
        tsize = s.sizeWithAttributes_(attrs)
        w = max(60.0, tsize.width + 32.0)
        h = tsize.height + 20.0 + TAIL

        self.bubble_view.message = msg
        self.bubble_view.attrs = attrs
        self.bubble_window.setContentSize_(NSMakeSize(w, h))
        self.bubble_view.setFrame_(NSMakeRect(0, 0, w, h))
        self._position_bubble()
        self.bubble_window.orderFront_(None)
        self.bubble_view.setNeedsDisplay_(True)
        self.bubble_until = time.time() + BUBBLE_DURATION

    def _position_bubble(self):
        bw = self.bubble_window.frame().size.width
        bx = self.x + SIZE / 2.0 - bw / 2.0
        by = self.y + SIZE - 6.0
        self.bubble_window.setFrameOrigin_(NSMakePoint(bx, by))

    # --- quit ---
    def quitApp_(self, sender):
        if self.timer is not None:
            self.timer.invalidate()
        if self.pet_window is not None:
            self.pet_window.orderOut_(None)
        if self.bubble_window is not None:
            self.bubble_window.orderOut_(None)
        release_lock()
        NSApplication.sharedApplication().terminate_(None)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    acquire_lock()

    app = NSApplication.sharedApplication()
    # Hide from the Dock / app switcher (runtime equivalent of LSUIElement).
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    controller = PetController.alloc().init()
    controller.setup()

    # Clean quit on Ctrl+C. The 1/FPS timer keeps the run loop ticking often
    # enough that Python can service the signal between frames.
    signal.signal(signal.SIGINT, lambda *_: controller.quitApp_(None))
    signal.signal(signal.SIGTERM, lambda *_: controller.quitApp_(None))

    try:
        app.run()
    finally:
        release_lock()


if __name__ == "__main__":
    main()
