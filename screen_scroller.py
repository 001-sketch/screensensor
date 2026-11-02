"""Camera hand-control prototype for scrolling and mouse clicks."""

from __future__ import annotations

import math
import csv
from datetime import datetime
from pathlib import Path
import time
from dataclasses import dataclass

import cv2
import mediapipe as mp
import pyautogui


CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FRAME_MARGIN = 80
SCROLL_DEAD_ZONE = 8
SCROLL_SCALE = 0.12
PINCH_DISTANCE = 0.055
CLICK_COOLDOWN = 0.8
CURSOR_SMOOTHING = 0.35


@dataclass
class ControlState:
    last_pinky_y: float | None = None
    pinch_started_at: float | None = None
    last_click_at: float = 0.0
    paused: bool = False
    recording: bool = False
    recording_label: str | None = None
    recording_samples: list[tuple[float, str, float, float, float, float]] | None = None


def distance(a: object, b: object) -> float:
    """Return normalized distance between two MediaPipe landmarks."""
    return math.hypot(a.x - b.x, a.y - b.y)


def map_to_screen(x: float, y: float, screen_width: int, screen_height: int) -> tuple[int, int]:
    """Map the camera control area to the user's screen."""
    usable_width = CAMERA_WIDTH - (FRAME_MARGIN * 2)
    usable_height = CAMERA_HEIGHT - (FRAME_MARGIN * 2)
    screen_x = (x - FRAME_MARGIN) / usable_width * screen_width
    screen_y = (y - FRAME_MARGIN) / usable_height * screen_height
    return (
        int(max(0, min(screen_width - 1, screen_x))),
        int(max(0, min(screen_height - 1, screen_y))),
    )


def draw_status(frame: object, state: ControlState, hand_found: bool, message: str) -> None:
    """Draw controls and current state on the camera preview."""
    height, width = frame.shape[:2]
    color = (0, 180, 0) if not state.paused else (0, 165, 255)
    cv2.rectangle(
        frame,
        (FRAME_MARGIN, FRAME_MARGIN),
        (width - FRAME_MARGIN, height - FRAME_MARGIN),
        color,
        2,
    )
    status = "PAUSED" if state.paused else "ACTIVE"
    cv2.putText(frame, f"{status} | {message}", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    cv2.putText(
        frame,
        "Index: cursor | Pinky: scroll | Pinch: click | R: record | Q: quit",
        (16, height - 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (235, 235, 235),
        1,
    )
    if not hand_found:
        cv2.putText(frame, "Show one hand to the camera", (16, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 200, 255), 2)
    if state.recording:
        label = state.recording_label or "none"
        cv2.putText(
            frame,
            f"RECORDING: {label} | U=up D=down S=stop label",
            (16, 78),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (0, 0, 255),
            2,
        )


def save_recording(state: ControlState) -> Path | None:
    """Save locally recorded landmark samples as a CSV file."""
    if not state.recording_samples:
        return None
    output_dir = Path(__file__).with_name("recordings")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"gesture_recording_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as recording_file:
        writer = csv.writer(recording_file)
        writer.writerow(("timestamp", "label", "pinky_x", "pinky_y", "index_x", "index_y"))
        writer.writerows(state.recording_samples)
    return output_path


def main() -> None:
    """Run the camera control loop until Q or Escape is pressed."""
    pyautogui.FAILSAFE = True
    screen_width, screen_height = pyautogui.size()
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not camera.isOpened():
        raise RuntimeError("Could not open the camera. Check that it is connected and not in use.")

    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    state = ControlState()
    state.recording_samples = []
    previous_cursor = pyautogui.position()

    try:
        with mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.6,
        ) as hands:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("The camera stopped returning frames.")

                frame = cv2.flip(frame, 1)
                result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                hand_found = bool(result.multi_hand_landmarks)
                message = "Waiting"

                if hand_found:
                    hand = result.multi_hand_landmarks[0]
                    mp_drawing.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                    index = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    thumb = hand.landmark[mp_hands.HandLandmark.THUMB_TIP]
                    pinky = hand.landmark[mp_hands.HandLandmark.PINKY_TIP]
                    pinch = distance(index, thumb) < PINCH_DISTANCE
                    if state.recording and state.recording_label:
                        state.recording_samples.append(
                            (
                                time.time(),
                                state.recording_label,
                                pinky.x,
                                pinky.y,
                                index.x,
                                index.y,
                            )
                        )

                    if not state.paused:
                        target = map_to_screen(
                            index.x * CAMERA_WIDTH,
                            index.y * CAMERA_HEIGHT,
                            screen_width,
                            screen_height,
                        )
                        cursor_x = int(previous_cursor.x + (target[0] - previous_cursor.x) * CURSOR_SMOOTHING)
                        cursor_y = int(previous_cursor.y + (target[1] - previous_cursor.y) * CURSOR_SMOOTHING)
                        pyautogui.moveTo(cursor_x, cursor_y, duration=0)
                        previous_cursor = pyautogui.position()

                        if state.last_pinky_y is not None:
                            movement = state.last_pinky_y - pinky.y
                            if abs(movement) * CAMERA_HEIGHT > SCROLL_DEAD_ZONE:
                                pyautogui.scroll(int(movement * CAMERA_HEIGHT * SCROLL_SCALE))
                                message = "Scrolling"
                        state.last_pinky_y = pinky.y

                        now = time.monotonic()
                        if pinch and state.pinch_started_at is None:
                            state.pinch_started_at = now
                        elif not pinch and state.pinch_started_at is not None:
                            if now - state.pinch_started_at >= 0.08 and now - state.last_click_at >= CLICK_COOLDOWN:
                                pyautogui.click()
                                state.last_click_at = now
                                message = "Click"
                            state.pinch_started_at = None
                        elif pinch:
                            message = "Pinch detected"
                    else:
                        message = "Paused"
                else:
                    state.last_pinky_y = None
                    state.pinch_started_at = None

                draw_status(frame, state, hand_found, message)
                cv2.imshow("Screen Sensor", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("p"):
                    state.paused = not state.paused
                    state.last_pinky_y = None
                elif key == ord("r"):
                    if state.recording:
                        output_path = save_recording(state)
                        state.recording = False
                        state.recording_label = None
                        state.recording_samples = []
                        if output_path:
                            print(f"Recording saved to {output_path}")
                    else:
                        state.recording = True
                        state.recording_label = None
                        state.recording_samples = []
                        print("Recording started. Press U for up, D for down, S to stop the current label.")
                elif key == ord("u") and state.recording:
                    state.recording_label = "scroll_up"
                elif key == ord("d") and state.recording:
                    state.recording_label = "scroll_down"
                elif key == ord("s") and state.recording:
                    state.recording_label = None
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
