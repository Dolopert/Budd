"""
Hand Gesture Ball Control
- Open hand / index finger: ball follows fingertip
- Fist (all fingers closed): ball freezes in place
- Peace sign (2 fingers up): ball launches upward with gravity
- Pinch (thumb + index close): ball grows/shrinks
- Thumbs up: ball changes color
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import math
import random
import time
import os
import urllib.request

# --- Model download ---
MODEL_PATH = os.path.join(os.path.expanduser("~"), "hand_landmarker.task")
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand landmarker model (~8 MB)...")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Model downloaded.")

# --- Landmark indices (MediaPipe 21-point hand) ---
WRIST = 0
THUMB_TIP, THUMB_IP = 4, 3
INDEX_TIP, INDEX_PIP = 8, 6
MIDDLE_TIP, MIDDLE_PIP = 12, 10
RING_TIP, RING_PIP = 16, 14
PINKY_TIP, PINKY_PIP = 20, 18

# Connections to draw
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (5,9),(9,10),(10,11),(11,12),
    (9,13),(13,14),(14,15),(15,16),
    (13,17),(17,18),(18,19),(19,20),
    (0,17),
]

def draw_landmarks(frame, lm, w, h):
    pts = [(int(l.x * w), int(l.y * h)) for l in lm]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], (0, 180, 255), 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 4, (80, 255, 80), -1)

# --- Gesture helpers ---

def finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def classify_gesture(lm):
    idx  = finger_up(lm, INDEX_TIP, INDEX_PIP)
    mid  = finger_up(lm, MIDDLE_TIP, MIDDLE_PIP)
    ring = finger_up(lm, RING_TIP, RING_PIP)
    pink = finger_up(lm, PINKY_TIP, PINKY_PIP)
    thumb_up = lm[THUMB_TIP].x < lm[THUMB_IP].x  # mirrored frame

    if dist(lm[THUMB_TIP], lm[INDEX_TIP]) < 0.05 and not mid and not ring and not pink:
        return "pinch"
    if not idx and not mid and not ring and not pink and not thumb_up:
        return "fist"
    if thumb_up and not idx and not mid and not ring and not pink:
        return "thumbs_up"
    if idx and mid and not ring and not pink:
        return "peace"
    if idx and not mid and not ring and not pink:
        return "point"
    if sum([idx, mid, ring, pink]) >= 3:
        return "open"
    return "other"


COLORS = [
    (0, 200, 255),
    (255, 100, 50),
    (50, 255, 100),
    (100, 50, 255),
    (255, 50, 200),
]


def main():
    ensure_model()

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Ball state
    bx, by = float(w // 2), float(h // 2)
    vx, vy = 0.0, 0.0
    radius = 40
    color_idx = 0
    ball_color = COLORS[color_idx]
    frozen = False
    gravity = 0.5
    bounce_damping = 0.75
    gesture_cooldown = 0
    pinch_base_dist = None
    pinch_base_radius = 40

    prev_time = time.time()
    frame_ts = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, frame_ts)
        frame_ts += 33

        gesture = "none"
        index_tip = None

        if result.hand_landmarks:
            lm = result.hand_landmarks[0]
            draw_landmarks(frame, lm, w, h)

            gesture = classify_gesture(lm)
            ix = int(lm[INDEX_TIP].x * w)
            iy = int(lm[INDEX_TIP].y * h)
            index_tip = (ix, iy)

            if gesture_cooldown > 0:
                gesture_cooldown -= 1

            if gesture == "fist":
                frozen = True
                vx, vy = 0, 0
                pinch_base_dist = None

            elif gesture in ("open", "point"):
                frozen = False
                bx += (ix - bx) * 0.25
                by += (iy - by) * 0.25
                vx = (ix - bx) * 0.1
                vy = (iy - by) * 0.1
                pinch_base_dist = None

            elif gesture == "peace" and gesture_cooldown == 0:
                frozen = False
                vy = -18
                vx = random.uniform(-4, 4)
                gesture_cooldown = 20
                pinch_base_dist = None

            elif gesture == "thumbs_up" and gesture_cooldown == 0:
                color_idx = (color_idx + 1) % len(COLORS)
                ball_color = COLORS[color_idx]
                gesture_cooldown = 30
                pinch_base_dist = None

            elif gesture == "pinch":
                d = dist(lm[THUMB_TIP], lm[INDEX_TIP])
                if pinch_base_dist is None:
                    pinch_base_dist = d
                    pinch_base_radius = radius
                else:
                    scale = d / max(pinch_base_dist, 1e-6)
                    radius = int(max(10, min(120, pinch_base_radius * scale)))

            else:
                pinch_base_dist = None

        # Physics
        if not frozen:
            vy += gravity
            bx += vx
            by += vy

            if bx - radius < 0:
                bx = float(radius); vx = abs(vx) * bounce_damping
            elif bx + radius > w:
                bx = float(w - radius); vx = -abs(vx) * bounce_damping

            if by - radius < 0:
                by = float(radius); vy = abs(vy) * bounce_damping
            elif by + radius > h:
                by = float(h - radius); vy = -abs(vy) * bounce_damping
                vx *= 0.92

        ibx, iby = int(bx), int(by)

        # Draw ball
        cv2.circle(frame, (ibx + 6, iby + 6), radius, (30, 30, 30), -1)
        cv2.circle(frame, (ibx, iby), radius, ball_color, -1)
        cv2.circle(frame, (ibx - radius // 4, iby - radius // 4), radius // 5, (255, 255, 255), -1)

        if index_tip:
            cv2.circle(frame, index_tip, 10, (0, 255, 255), 2)

        # FPS
        now = time.time()
        fps = 1 / max(now - prev_time, 1e-6)
        prev_time = now

        gesture_labels = {
            "fist": "FREEZE", "open": "FOLLOW", "point": "FOLLOW",
            "peace": "LAUNCH!", "thumbs_up": "COLOR", "pinch": "RESIZE",
            "none": "---", "other": "---",
        }
        label = gesture_labels.get(gesture, gesture)

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (300, 160), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

        cv2.putText(frame, f"Gesture: {label}", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 200), 2)
        cv2.putText(frame, f"FPS: {fps:.0f}", (12, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
        cv2.putText(frame, f"Ball R: {radius}", (12, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 1)
        if frozen:
            cv2.putText(frame, "[ FROZEN ]", (12, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 80, 255), 2)

        cv2.putText(frame, "Q = quit", (w - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

        guide = ["Fist=Freeze", "Open/Point=Follow", "Peace=Launch", "ThumbUp=Color", "Pinch=Resize"]
        for i, tip in enumerate(guide):
            cv2.putText(frame, tip, (10 + i * 240, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 100), 1)

        cv2.imshow("Hand Gesture Ball", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    landmarker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
