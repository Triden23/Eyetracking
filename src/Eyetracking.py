import cv2
import tkinter as tk
from threading import Thread
import time
import math
import json
from cvzone.FaceMeshModule import FaceMeshDetector  # ✅ cvzone import


class Eyetracking:
    def __init__(self):
        # Load JSON
        self.dataPath = "data.json"
        self.data = json.load(open(self.dataPath))

        # cvzone setup
        self.cap = cv2.VideoCapture(0)
        self.detector = FaceMeshDetector(maxFaces=1)

        # Tkinter setup
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Configuration
        self.rows, self.cols = 4, 4
        self.buttons = []
        self.button_locked = False
        self.DWELL_SECONDS = 4

        # Counters
        self.PageNumber = 0
        self.PageMax = len(self.data.get("Pages")) - 1

        # Track dwell state
        self.last_gaze_index = None
        self.gaze_start_time = None

        # Canvas
        self.root.state = "normal"
        self.canvas = tk.Canvas(self.root, width=self.screen_width, height=self.screen_height, highlightthickness=0)
        self.canvas.place(x=0, y=0)
        self.ring_id = None
        self.text_id = None

        self.create_buttons()
        Thread(target=self.track_gaze, daemon=True).start()
        self.root.mainloop()

    def getText(self, row, col):
        page = f"{self.PageNumber}"
        return self.data.get(page, {}).get(f"{row}_{col}", "")

    def pause_play(self):
        self.button_locked = not self.button_locked
        print("Paused" if self.button_locked else "Unpaused")
        for btn in self.buttons:
            if btn['text'] != "Pause/Play":
                btn.config(state="disabled" if self.button_locked else "normal")

    def help_call(self, arg):
        print("Help called")  # Placeholder

    def updatePage(self, direction):
        if direction == "Next":
            self.PageNumber = (self.PageNumber + 1) % (self.PageMax + 1)
        elif direction == "Back":
            self.PageNumber = (self.PageNumber - 1 + (self.PageMax + 1)) % (self.PageMax + 1)
        self.update_button_images()

    def get_button_command(self, row, col):
        def command():
            if row == 3 and col == 0:
                self.updatePage("Back")
            elif row == 3 and col == 3:
                self.updatePage("Next")
            elif row == 3 and col == 2:
                self.help_call("next")
            elif row == 3 and col == 1:
                self.pause_play()
            else:
                txt = self.getText(row, col)
                print(txt)  # Replace with TTS
        return command

    def create_buttons(self):
        for r in range(self.rows):
            for c in range(self.cols):
                label = "Pause/Play" if (r == 3 and c == 1) else f"Button {r * self.cols + c + 1}"
                btn = tk.Button(self.root, text=label, bg="lightgrey", font=("Arial", 18),
                                command=self.get_button_command(r, c))
                btn.place(x=c * self.screen_width // self.cols,
                          y=r * self.screen_height // self.rows,
                          width=self.screen_width // self.cols,
                          height=self.screen_height // self.rows)
                self.buttons.append(btn)

    def draw_progress_ring(self, x, y, size, progress):
        if self.ring_id:
            self.canvas.delete(self.ring_id)
            self.ring_id = None
        if self.text_id:
            self.canvas.delete(self.text_id)
            self.text_id = None
        angle = int(360 * progress)
        self.ring_id = self.canvas.create_arc(
            x, y, x + size, y + size,
            start=90, extent=-angle,
            style="arc", outline="blue", width=5
        )
        seconds_left = max(0, math.ceil(self.DWELL_SECONDS * (1 - progress)))
        self.text_id = self.canvas.create_text(
            x + size // 2, y + size // 2,
            text=str(seconds_left),
            font=("Arial", 24, "bold"),
            fill="blue"
        )

    def update_button_images(self):
        print("Updating Images")  # Placeholder

    def update_buttons(self, gaze_x, gaze_y):
        current_index = None
        for i, btn in enumerate(self.buttons):
            if btn['state'] == "disabled":
                continue
            row = i // self.cols
            col = i % self.cols
            x1 = col * self.screen_width // self.cols
            y1 = row * self.screen_height // self.rows
            x2 = x1 + self.screen_width // self.cols
            y2 = y1 + self.screen_height // self.rows
            if x1 <= gaze_x <= x2 and y1 <= gaze_y <= y2:
                current_index = i
                break

        for i, btn in enumerate(self.buttons):
            btn.config(bg="red" if i == current_index else "lightgrey")

        if current_index != self.last_gaze_index:
            self.last_gaze_index = current_index
            self.gaze_start_time = time.time() if current_index is not None else None
        elif current_index is not None and self.gaze_start_time is not None:
            elapsed = time.time() - self.gaze_start_time
            progress = elapsed / self.DWELL_SECONDS
            row = current_index // self.cols
            col = current_index % self.cols
            btn_x = col * self.screen_width // self.cols
            btn_y = row * self.screen_height // self.rows
            size = min(self.screen_width // self.cols, self.screen_height // self.rows) // 2
            self.draw_progress_ring(btn_x + size // 2, btn_y + size // 2, size, min(progress, 1.0))
            if progress >= 1.0:
                self.buttons[current_index].invoke()
                self.gaze_start_time = None
                self.canvas.delete("all")
        else:
            self.canvas.delete("all")

    def track_gaze(self):
        while self.cap.isOpened():
            success, frame = self.cap.read()
            if not success:
                continue

            frame = cv2.flip(frame, 1)
            frame, faces = self.detector.findFaceMesh(frame, draw=False)

            if faces:
                face = faces[0]
                left_eye = face[33]
                right_eye = face[263]

                gaze_x = (left_eye[0] + right_eye[0]) / 2
                gaze_y = (left_eye[1] + right_eye[1]) / 2

                # Convert to screen coordinates
                self.update_buttons(gaze_x, gaze_y)

            try:
                self.root.update_idletasks()
                self.root.update()
            except tk.TclError:
                break

        self.cap.release()


if __name__ == "__main__":
    Eyetracking()