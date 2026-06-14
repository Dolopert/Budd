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
import math
import random
import time

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# --- Gesture detection helpers ---

def finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def count_fingers_up(lm):
    fingers = [
        finger_up(lm, 8, 6),   # index
        finger_up(lm, 12, 10),  # middle
        finger_up(lm, 16, 14),  # ring
        finger_up(lm, 20, 18),  # pinky
    ]
    # thumb: check x-axis (right hand)
    thumb_up = lm[4].x < lm[3].x
    return thumb_up, fingers

def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def classify_gesture(lm):
    thumb_up, fingers = count_fingers_up(lm)
    idx, mid, ring, pink = fingers

    # Pinch: thumb and index close together, others curled
    if dist(lm[4], lm[8]) < 0.05 and not mid and not ring and not pink:
        return "pinch"
    # Fist: all fingers down
    if not any(fingers) and not thumb_up:
        return "fist"
    # Thumbs up: only thumb extended
    if thumb_up and not any(fingers):
        return "thumbs_up"
    # Peace: index + middle only
    if idx and mid and not ring and not pink:
        return "peace"
    # Point: only index
    if idx and not mid and not ring and not pink:
        return "point"
    # Open hand: 4+ fingers up
    if sum(fingers) >= 3:
        return "open"
    return "other"


COLORS = [
    (0, 200, 255),   # yellow
    (255, 100, 50),  # blue
    (50, 255, 100),  # green
    (100, 50, 255),  # red-ish
    (255, 50, 200),  # pink
]

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Ball state
    bx, by = w // 2, h // 2
    vx, vy = 0.0, 0.0
    radius = 40
    color_idx = 0
    ball_color = COLORS[color_idx]
    frozen = False
    gravity = 0.5
    bounce_damping = 0.75
    last_gesture = ""
    gesture_cooldown = 0
    pinch_base_dist = None
    pinch_base_radius = 40

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )

    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        gesture = "none"
        index_tip = None

        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0].landmark
            mp_draw.draw_landmarks(
                frame,
                result.multi_hand_landmarks[0],
                mp_hands.HAND_CONNECTIONS,
                mp_draw.DrawingSpec(color=(80, 255, 80), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(0, 180, 255), thickness=2),
            )

            gesture = classify_gesture(lm)
            ix = int(lm[8].x * w)
            iy = int(lm[8].y * h)
            index_tip = (ix, iy)

            if gesture_cooldown > 0:
                gesture_cooldown -= 1

            if gesture == "fist":
                frozen = True
                vx, vy = 0, 0
                pinch_base_dist = None

            elif gesture == "open" or gesture == "point":
                frozen = False
                # Smoothly move ball toward fingertip
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
                current_dist = dist(lm[4], lm[8])
                if pinch_base_dist is None:
                    pinch_base_dist = current_dist
                    pinch_base_radius = radius
                else:
                    scale = current_dist / pinch_base_dist
                    radius = int(max(10, min(120, pinch_base_radius * scale)))

            else:
                pinch_base_dist = None

        # Physics (when not frozen)
        if not frozen:
            vy += gravity
            bx += vx
            by += vy

            # Wall bounces
            if bx - radius < 0:
                bx = radius
                vx = abs(vx) * bounce_damping
            elif bx + radius > w:
                bx = w - radius
                vx = -abs(vx) * bounce_damping

            if by - radius < 0:
                by = radius
                vy = abs(vy) * bounce_damping
            elif by + radius > h:
                by = h - radius
                vy = -abs(vy) * bounce_damping
                vx *= 0.92  # friction

        bx = int(bx)
        by = int(by)

        # Draw ball shadow
        cv2.circle(frame, (bx + 6, by + 6), radius, (30, 30, 30), -1)
        # Draw ball
        cv2.circle(frame, (bx, by), radius, ball_color, -1)
        # Highlight
        cv2.circle(frame, (bx - radius // 4, by - radius // 4), radius // 5, (255, 255, 255), -1)

        # Draw fingertip cursor
        if index_tip:
            cv2.circle(frame, index_tip, 10, (0, 255, 255), 2)

        # FPS
        now = time.time()
        fps = 1 / max(now - prev_time, 1e-6)
        prev_time = now

        # HUD
        gesture_labels = {
            "fist": "FREEZE",
            "open": "FOLLOW",
            "point": "FOLLOW",
            "peace": "LAUNCH!",
            "thumbs_up": "COLOR",
            "pinch": "RESIZE",
            "none": "---",
            "other": "---",
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

        # Gesture guide bottom strip
        guide = [
            "Fist=Freeze",
            "Open/Point=Follow",
            "Peace=Launch",
            "ThumbUp=Color",
            "Pinch=Resize",
        ]
        for i, tip in enumerate(guide):
            cv2.putText(frame, tip, (10 + i * 240, h - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 100), 1)

        cv2.imshow("Hand Gesture Ball", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
