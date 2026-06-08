import cv2
import mediapipe as mp
from collections import deque
import socket

# ---------------- Mediapipe setup ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6)
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

# ---------------- Parametri ----------------
total_lines = 60
server_host = "localhost"
server_port = 9999

fist_history = deque(maxlen=5)
LINE_SCALE = 0.9
PINCH_BUFFER_LEN = 10
pinch_buffer = deque(maxlen=PINCH_BUFFER_LEN)

selection_locked = False
last_sent_start = -1
last_sent_end = -1

# ---------------- Gesture stabilization ----------------
gesture_history = deque(maxlen=5)
last_sent_option = -1

# ---------------- Slanje u IntelliJ ----------------
def send_selection(start, end):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_host, server_port))
            s.sendall(f"{start},{end}\n".encode())
        print(f"SELECTION SENT: {start}-{end}")
    except Exception as e:
        print("Could not send selection to plugin!", e)

def trigger_ai():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_host, server_port))
            s.sendall(b"AI:")
        print("AI Assistant triggered!")
    except Exception as e:
        print("Could not trigger AI Assistant!", e)

def send_ai_option(option):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_host, server_port))
            s.sendall(f"AI_OPTION:{option}\n".encode())
        print(f"AI OPTION SENT: {option}")
    except Exception as e:
        print("Could not send AI option!", e)

# ---------------- Utility ----------------
def y_to_line(y, height):
    line = int((y / height) * total_lines * LINE_SCALE)
    return max(0, min(line, total_lines - 1))

# ---------------- Fist detection ----------------
def detect_fist(hand):
    folded = 0
    for tip_id, pip_id in [
        (mp_hands.HandLandmark.INDEX_FINGER_TIP, mp_hands.HandLandmark.INDEX_FINGER_PIP),
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP),
        (mp_hands.HandLandmark.PINKY_TIP, mp_hands.HandLandmark.PINKY_PIP)
    ]:
        if hand.landmark[tip_id].y > hand.landmark[pip_id].y + 0.02:
            folded += 1
    thumb_tip = hand.landmark[mp_hands.HandLandmark.THUMB_TIP].x
    index_pip = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].x
    thumb_folded = abs(thumb_tip - index_pip) < 0.12
    return folded >= 3 and thumb_folded

# ---------------- Rock sign detection ----------------
def detect_rock_sign(hand):
    folded_count = 0
    for tip_id, pip_id in [
        (mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP),
        (mp_hands.HandLandmark.RING_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_PIP)
    ]:
        if hand.landmark[tip_id].y > hand.landmark[pip_id].y + 0.02:
            folded_count += 1

    thumb_out = hand.landmark[mp_hands.HandLandmark.THUMB_TIP].y < hand.landmark[mp_hands.HandLandmark.THUMB_MCP].y
    index_out = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    pinky_out = hand.landmark[mp_hands.HandLandmark.PINKY_TIP].y < hand.landmark[mp_hands.HandLandmark.PINKY_PIP].y

    return folded_count == 2 and thumb_out and index_out and pinky_out

# ---------------- Finger gestures ----------------
def detect_one_finger(hand):
    index_up = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_down = hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y > hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_down = hand.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y > hand.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_down = hand.landmark[mp_hands.HandLandmark.PINKY_TIP].y > hand.landmark[mp_hands.HandLandmark.PINKY_PIP].y
    thumb_in = abs(hand.landmark[mp_hands.HandLandmark.THUMB_TIP].x - hand.landmark[mp_hands.HandLandmark.WRIST].x) < 0.05
    return index_up and middle_down and ring_down and pinky_down and thumb_in

def detect_two_fingers(hand):
    index_up = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_up = hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_down = hand.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y > hand.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_down = hand.landmark[mp_hands.HandLandmark.PINKY_TIP].y > hand.landmark[mp_hands.HandLandmark.PINKY_PIP].y
    thumb_in = abs(hand.landmark[mp_hands.HandLandmark.THUMB_TIP].x - hand.landmark[mp_hands.HandLandmark.WRIST].x) < 0.05
    return index_up and middle_up and ring_down and pinky_down and thumb_in

def detect_three_fingers(hand):
    thumb_up = hand.landmark[mp_hands.HandLandmark.THUMB_TIP].y < hand.landmark[mp_hands.HandLandmark.THUMB_IP].y
    index_up = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_up = hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < hand.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_down = hand.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y > hand.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_down = hand.landmark[mp_hands.HandLandmark.PINKY_TIP].y > hand.landmark[mp_hands.HandLandmark.PINKY_PIP].y
    return thumb_up and index_up and middle_up and ring_down and pinky_down

def detect_gesture_option(hand):
    if detect_one_finger(hand):
        return 1
    elif detect_two_fingers(hand):
        return 2
    elif detect_three_fingers(hand):
        return 3
    return None

# ---------------- Main Loop ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (640, 480))
    h, w, _ = frame.shape

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    # ---------------- Reset overlay ----------------
    overlay_lines = []

    if results.multi_hand_landmarks:
        hand = results.multi_hand_landmarks[0]
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        # ---------------- Gesture option sending (stabilized) ----------------
        option = detect_gesture_option(hand)
        gesture_history.append(option)
        if option is not None and sum(1 for g in gesture_history if g == option) >= 3:
            if last_sent_option != option:
                send_ai_option(option)
                last_sent_option = option

        # ---------------- Rock sign detection (close AI) ----------------
        if detect_rock_sign(hand):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((server_host, server_port))
                    s.sendall(b"AI:CLOSE\n")
                print("AI Assistant close command sent")
            except Exception as e:
                print("Could not send close command!", e)

        # ---------------- Pinch selection ----------------
        thumb = hand.landmark[mp_hands.HandLandmark.THUMB_TIP]
        index = hand.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]

        pinch_start_line = y_to_line(thumb.y * h, h)
        pinch_end_line = y_to_line(index.y * h, h)
        current_start = min(pinch_start_line, pinch_end_line)
        current_end = max(pinch_start_line, pinch_end_line)
        pinch_buffer.append((current_start, current_end))

        # ---------------- Fist detection ----------------
        fist_raw = detect_fist(hand)
        fist_history.append(fist_raw)
        stable_fist = sum(fist_history) >= 3

        if stable_fist and not selection_locked:
            selection_locked = True
            start_buffer = [s for s, e in pinch_buffer]
            end_buffer = [e for s, e in pinch_buffer]
            last_sent_start = min(start_buffer)
            last_sent_end = max(end_buffer)
            send_selection(last_sent_start, last_sent_end)
            trigger_ai()

        if not selection_locked:
            if current_start != last_sent_start or current_end != last_sent_end:
                last_sent_start = current_start
                last_sent_end = current_end
                send_selection(last_sent_start, last_sent_end)

        # ---------------- UI overlay ----------------
        # Fiksne Y koordinate za opcije da se ne preklapaju
        option_y_positions = {1: 90, 2: 120, 3: 150}
        for opt_num, y in option_y_positions.items():
            text = f"Option {opt_num}" + (" <-" if last_sent_option == opt_num else "")
            cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0) if last_sent_option == opt_num else (200, 200, 200), 2)

        cv2.putText(frame, f"FIST: {stable_fist}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if stable_fist else (255, 0, 0), 2)
        cv2.putText(frame, f"Selecting: {current_start} -> {current_end}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    else:
        selection_locked = False
        last_sent_start = -1
        last_sent_end = -1
        pinch_buffer.clear()
        fist_history.clear()
        gesture_history.clear()
        last_sent_option = -1

    cv2.imshow("Touchless Code Selector", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
