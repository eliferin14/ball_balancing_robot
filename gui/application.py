import tkinter as tk
from tkinter import ttk

from ttkthemes import ThemedTk

class RobotApp(ThemedTk):
    def __init__(self, robot, *args, **kwargs):
        ThemedTk.__init__(self, *args, **kwargs)
        # Adding a title to the window
        self.wm_title("Test Application")

        # Store robot as a parameter
        self.robot = robot

        # Target variables
        self.target_velx = tk.DoubleVar(self, value=0)
        self.target_vely = tk.DoubleVar(self, value=0)
        self.target_height = tk.DoubleVar(self, value=50)

        targetSelectionFrame = ttk.LabelFrame(self, text="Target")
        targetSelectionFrame.grid()

        labeltest = ttk.Label(targetSelectionFrame, text="Test")
        labeltest.grid()

        buttonTest = ttk.Button(targetSelectionFrame, text="Hello")
        buttonTest.grid()

    def show_frame(self, cont):
        frame = self.frames[cont]
        # raises the current frame to the top
        frame.tkraise()

class MainPage(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent)
        
        # Frame for the target selection
        












class SidePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="This is the Side Page")
        label.pack(padx=10, pady=10)

        switch_window_button = tk.Button(
            self,
            text="Go to the Completion Screen",
            command=lambda: controller.show_frame(CompletionScreen),
        )
        switch_window_button.pack(side="bottom", fill=tk.X)


class CompletionScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Completion Screen, we did it!")
        label.pack(padx=10, pady=10)
        switch_window_button = ttk.Button(
            self, text="Return to menu", command=lambda: controller.show_frame(MainPage)
        )
        switch_window_button.pack(side="bottom", fill=tk.X)
