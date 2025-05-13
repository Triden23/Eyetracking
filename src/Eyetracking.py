import cv2
import mediapipe as mp
import tkinter as tk
from threading import Thread
import time
import math
import json

# MediaPipe setup
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
dataPath = "data.json"
data = json.load(open(dataPath))

# Tkinter setup
root = tk.Tk()
root.attributes("-fullscreen", True)

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Configuration
rows, cols = 4, 4
buttons = []
button_locked = False
DWELL_SECONDS = 4

# Counters
Page = 0
PageMax = 0

# Current TTS Text
text = ""

# Track dwell state
last_gaze_index = None
gaze_start_time = None

# Overlay canvas for ring and timer
canvas = tk.Canvas(root, width=screen_width, height=screen_height, bg='', highlightthickness=0)
canvas.place(x=0, y=0)

ring_id = None
text_id = None


def getText(Row, Col):

    text = data.get(f"{Page}", {}).get(f"{Row}_{Col}")


def pause_play():
    global button_locked
    button_locked = not button_locked
    print("Paused" if button_locked else "Unpaused")
    for btn in buttons:
        if btn['text'] != "Pause/Play":
            btn.config(state="disabled" if button_locked else "normal")


# Assign methods to specific buttons
def get_button_command(row, col):
    if row == 3 and col == 0:
        return back
    elif row == 3 and col == 3:
        return next
    elif row == 3 and col == 2:
        return help_call
    elif row == 3 and col == 1:
        return pause_play
    else:
        getText(row, col)  # Replace with TTS play later per sophias idea
        print(text)
        # call tts


# Create button grid
for r in range(rows):
    for c in range(cols):
        label = "Pause/Play" if (r == 3 and c == 1) else f"Button {r * cols + c + 1}"
        btn = tk.Button(root, text=label, bg="lightgrey", font=("Arial", 18), command=get_button_command(r, c))
        btn.place(x=c * screen_width // cols, y=r * screen_height // rows,
                  width=screen_width // cols, height=screen_height // rows)
        buttons.append(btn)


# Draw ring and countdown
def draw_progress_ring(x, y, size, progress):
    global ring_id, text_id
    canvas.delete(ring_id)
    canvas.delete(text_id)

    angle = int(360 * progress)
    ring_id = canvas.create_arc(
        x, y, x + size, y + size,
        start=90, extent=-angle,
        style="arc", outline="blue", width=5
    )

    seconds_left = max(0, math.ceil(DWELL_SECONDS * (1 - progress)))
    text_id = canvas.create_text(
        x + size // 2, y + size // 2,
        text=str(seconds_left),
        font=("Arial", 24, "bold"),
        fill="blue"
    )


# Page number control and edge casing
def updatePage(NextBack):
    if (NextBack == "Next"):
        Page += 1
        if (Page > PageMax):
            Page = 0
    elif (NextBack == "Back"):
        Page = Page + 1
        if (Page < 0):
            Page = PageMax


# Update Images
def update_button_images():
    # Does nothing right now but will update images
    print("Updating Images")


# Highlight, dwell, and visual update
def update_buttons(gaze_x, gaze_y):
    global last_gaze_index, gaze_start_time

    current_index = None
    for i, btn in enumerate(buttons):
        if btn['state'] == "disabled":
            continue
        row = i // cols
        col = i % cols
        x1 = col * screen_width // cols
        y1 = row * screen_height // rows
        x2 = x1 + screen_width // cols
        y2 = y1 + screen_height // rows

        if x1 <= gaze_x <= x2 and y1 <= gaze_y <= y2:
            current_index = i
            break

    # Visual highlight
    for i, btn in enumerate(buttons):
        btn.config(bg="red" if i == current_index else "lightgrey")

    # Dwell logic
    if current_index != last_gaze_index:
        last_gaze_index = current_index
        gaze_start_time = time.time() if current_index is not None else None
        canvas.delete("all")
    elif current_index is not None and gaze_start_time is not None:
        elapsed = time.time() - gaze_start_time
        progress = elapsed / DWELL_SECONDS
        row = current_index // cols
        col = current_index % cols
        btn_x = col * screen_width // cols
        btn_y = row * screen_height // rows
        size = min(screen_width // cols, screen_height // rows) // 2
        draw_progress_ring(btn_x + size // 2, btn_y + size // 2, size, min(progress, 1.0))
        if progress >= 1.0:
            buttons[current_index].invoke()
            gaze_start_time = None
            canvas.delete("all")
    else:
        canvas.delete("all")


# Eye tracking loop
def track_gaze():
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(frame_rgb)

        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                left_eye = face_landmarks.landmark[33]
                right_eye = face_landmarks.landmark[263]
                gaze_x = (left_eye.x + right_eye.x) / 2 * screen_width
                gaze_y = (left_eye.y + right_eye.y) / 2 * screen_height
                update_buttons(gaze_x, gaze_y)

        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            break

    cap.release()


Thread(target=track_gaze, daemon=True).start()
root.mainloop()
