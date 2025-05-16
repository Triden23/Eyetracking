import cv2
import tkinter as tk
from threading import Thread
import time
import math
import json

from PIL.ImageChops import screen
from cvzone.FaceMeshModule import FaceMeshDetector  #Maybe change the library in use. Do more research


class Eyetracking:
    def __init__(self):
        # Load JSON
        self.dataPath = "data.json"
        self.data = json.load(open(self.dataPath))

        self.run = True

        # Modes

        # DO NOT FUCKING CHANGE THIS ILL KILL YOU
        self.MODE_CALIBRATE = "CALIBRATE"
        self.MODE_CALIBRATE_WAIT = "CALIBRATE_WAIT"
        self.MODE_LOCK = "LOCK"
        self.MODE_NORMAL = "NORMAL"

        #Assign the current operation to this variable to help lock out anything
        self.Current_Mode = self.MODE_CALIBRATE

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

        # KeyListener(Space bar only in CALIBRATE_WAIT)
        self.canvas.bind("<KeyPress>", self.HandleKeyPress)

        # Calibration vars
        self.CalibrationCounter = 0
        self.Calibration_Data = CalibrationData()
        self.Calibration_Point = self.canvas.create_oval(0, 0, 0, 0)
        self.Calibration_Continue_Flag = False
        self.Calibration_Capture_Flag = False
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

            if progress >= 1.0:
                self.buttons[current_index].invoke()
                self.gaze_start_time = None
                self.canvas.delete("all")
        else:
            self.canvas.delete("all")

    def track_gaze(self):
        while self.cap.isOpened() and self.run :

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

                    print(f"{gaze_x}, {gaze_y}")

                    if self.Current_Mode == self.MODE_CALIBRATE or self.Current_Mode == self.MODE_CALIBRATE_WAIT:
                        self.Calibrate()
                        if self.Current_Mode == self.MODE_CALIBRATE_WAIT and self.Calibration_Capture_Flag:
                            self.Calibration_Data.setBaseData(self.CalibrationCounter, left_eye[0], left_eye[1], right_eye[0], right_eye[1])

                            self.Calibration_Capture_Flag = False
                            self.Current_Mode = False

                            self.CalibrationCounter += 1
                            if self.CalibrationCounter > 3:
                                self.CalibrationCounter = 0
                    else:
                        # Convert to screen coordinates
                        self.update_buttons(gaze_x, gaze_y)

                try:
                    self.root.update_idletasks()
                    self.root.update()
                except tk.TclError:
                    self.run = False

            self.cap.release()


    def calibrationMarker(self,x,y):
        size = 50
        self.canvas.delete(self.Calibration_Point)
        self.Calibration_Point = self.canvas.create_oval(x, x + size, y, y + size, fill="red")
        self.Current_Mode = self.MODE_CALIBRATE_WAIT
    '''
    
    Get 4 points from the middle of the screen
    
    Draw a circle wait for user input, input triggers a gather point, passing to Calibration object one by one.
    Normalize data -> Pull up webcam on full screen (Testing only) Optional check again
    
    
    '''

    def Calibrate(self):
        x = 0
        y = 0
        if self.Current_Mode == self.MODE_CALIBRATE:
            if self.CalibrationCounter == 0:
                x = self.screen_width/2
                y = 0
            elif self.CalibrationCounter == 1:
                x = self.screen_width
                y = self.screen_height/2
            elif self.CalibrationCounter == 2:
                x = self.screen_width/2
                y = self.screen_height
            elif self.CalibrationCounter == 3:
                x = 0
                y = self.screen_height/2

            self.calibrationMarker(x,y)
            self.Current_Mode = self.MODE_CALIBRATE_WAIT
                #Get gaze data

    def HandleKeyPress(self, event):
        if(self.Current_Mode == self.MODE_CALIBRATE_WAIT):
            print(f"{event.key} pressed") #Temp to grab keypress
            if(event.key == 32):
                self.Calibration_Capture_Flag = True



class CalibrationData:
    def __init__(self):

        # Top point

        self.leftEye_TopOffSet_x = 0
        self.leftEye_TopOffSet_y = 0

        self.rightEye_TopOffSet_x = 0
        self.rightEye_TopOffSet_y = 0

        # Right point

        self.leftEye_RightOffSet_x = 0
        self.leftEye_RightOffSet_y = 0

        self.rightEye_RightOffSet_x = 0
        self.rightEye_RightOffSet_y = 0

        # Bottom point

        self.leftEye_BottomOffSet_x = 0
        self.leftEye_BottomOffSet_y = 0

        self.rightEye_BottomOffSet_x = 0
        self.rightEye_BottomOffSet_y = 0

        # Left point

        self.leftEye_LeftOffSet_x = 0
        self.rightEye_LeftOffSet_x = 0

        self.leftEye_LeftOffSet_y = 0
        self.rightEye_LeftOffSet_y = 0

        # Normalized Data (the middle of 2 points)

        self.Normalized_TopOffSet_x = 0
        self.Normalized_TopOffSet_y = 0

        self.Normalized_RightOffSet_x = 0
        self.Normalized_RightOffSet_y = 0

        self.Normalized_BottomOffSet_x = 0
        self.Normalized_BottomOffSet_y = 0

        self.Normalized_LeftOffSet_x = 0
        self.Normalized_LeftOffSet_y = 0

        #Top then clock wise
        self.NormalizedList = [[]]



    def normalizeData(self):
        self.Normalized_TopOffSet_x = (self.rightEye_TopOffSet_x + self.leftEye_TopOffSet_x)/2
        self.Normalized_TopOffSet_y = (self.rightEye_TopOffSet_y + self.leftEye_TopOffSet_y)/2

        self.Normalized_RightOffSet_x = (self.rightEye_RightOffSet_x + self.leftEye_RightOffSet_x)/2
        self.Normalized_RightOffSet_y = (self.rightEye_RightOffSet_y + self.leftEye_RightOffSet_y)/2

        self.Normalized_BottomOffSet_x = (self.rightEye_BottomOffSet_x + self.leftEye_BottomOffSet_x)/2
        self.Normalized_BottomOffSet_y = (self.rightEye_BottomOffSet_y + self.leftEye_BottomOffSet_y)/2

        self.Normalized_LeftOffSet_x = (self.rightEye_LeftOffSet_x + self.leftEye_LeftOffSet_x)/2
        self.Normalized_LeftOffSet_y = (self.rightEye_LeftOffSet_y + self.leftEye_LeftOffSet_y)/2

        self.Normalized_List = [[self.Normalized_TopOffSet_x,self.Normalized_TopOffSet_y],
                                [self.Normalized_RightOffSet_x,self.Normalized_RightOffSet_y],
                                [self.Normalized_BottomOffSet_x,self.Normalized_BottomOffSet_y],
                                [self.Normalized_LeftOffSet_x,self.Normalized_LeftOffSet_y]]


    # Returns X and Y of offset index
    def getNormalizedData(self, index):
        if index >= len(self.NormalizedList):
            print("Index out of range returning default of index - 0")
            return self.NormalizedList[0]
        else:
            return self.NormalizedList[index]

    # Sets the value, X1,Y1 left Eye, X2,Y2 right eye
    # Top,Right,Bottom,Right in that order 0-3
    def setBaseData(self, index, x1, y1, x2, y2):
        if index >= len(self.NormalizedList):
            print("Index out of bounds")
        else:
            if index == "0":
                self.leftEye_TopOffSet_x = x1
                self.leftEye_TopOffSet_y = y1
                self.rightEye_TopOffSet_x = x2
                self.rightEye_TopOffSet_y = y2
            elif index == 1:
                self.leftEye_RightOffSet_x = x1
                self.leftEye_RightOffSet_y = y1
                self.rightEye_RightOffSet_x = x2
                self.rightEye_RightOffSet_y = y2
            elif index == 2:
                self.leftEye_BottomOffSet_x = x1
                self.leftEye_BottomOffSet_y = y1
                self.rightEye_BottomOffSet_x = x2
                self.rightEye_BottomOffSet_y = y2
            elif index == 3:
                self.leftEye_LeftOffSet_x = x1
                self.leftEye_LeftOffSet_y = y1
                self.rightEye_LeftOffSet_x = x2
                self.rightEye_LeftOffSet_y = y2

if __name__ == "__main__":
    Eyetracking()