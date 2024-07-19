import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk
from kinematics.robot3RRS import robot3RRS

class RobotApp(ThemedTk):
    def __init__(self, *args, **kwargs):
        ThemedTk.__init__(self, *args, **kwargs)

        # Adding a title to the window
        self.wm_title("Ball Balancing Robot")

        # Define styles for widgets
        self.style = ttk.Style(self)
        #self.style.configure('my.TFrame', background='red')
        self.style.configure('TLabelframe', padding=10)

        # Create a general container frame: everything goes inside here
        mainFrame = ttk.Frame(self, height=720, width=1080, padding=10)
        mainFrame.grid(row=0,column=0,sticky='nesw')

        # Robot parameters variables
        self.baseRadius = tk.DoubleVar(self, value=50)
        self.platRadius = tk.DoubleVar(self, value=40)
        self.armLength = tk.DoubleVar(self, value=40)
        self.forearmLength = tk.DoubleVar(self, value=60)

        # Target variables
        self.target_velx = tk.DoubleVar(self, value=0)
        self.target_vely = tk.DoubleVar(self, value=0)
        self.target_height = tk.DoubleVar(self, value=50)
        self.target_velx.trace_add('write', self.onTargetVelxChange)
        self.target_vely.trace_add('write', self.onTargetVelyChange)
        self.target_height.trace_add('write', self.onTargetHeightChange)

        # Declare robot creation frame
        self.createRobotCreationFrame(mainFrame)

        # Declare target selection frame
        self.createTargetSelectionFrame(mainFrame)

        # Declare canvas frame
        self.createCanvasFrame(mainFrame)

    def createRobotCreationFrame(self, master):
        robotCreationFrame = ttk.LabelFrame(master, text="Robot parameters")
        robotCreationFrame.grid(row=0,column=0,sticky='nesw')
        ph_labelParameters = ttk.Label(robotCreationFrame, text='Parameters')
        ph_labelParameters.grid()

    def createTargetSelectionFrame(self, master):        
        targetSelectionFrame = ttk.LabelFrame(master, text="Target")
        targetSelectionFrame.grid(row=1,column=0,sticky='nesw')

        velxSlider = ttk.Scale(targetSelectionFrame, from_=-1, to=1, orient='horizontal', command=self.velxScaleUpdate)
        velxSlider.grid()

        velySlider = ttk.Scale(targetSelectionFrame, from_=-1, to=1, orient='horizontal', command=self.velyScaleUpdate)
        velySlider.grid()
        
        heightSlider = ttk.Scale(targetSelectionFrame, from_=0, to=100, orient='horizontal', command=self.heightScaleUpdate)
        heightSlider.grid()

    def createCanvasFrame(self, master):
        canvasFrame = ttk.LabelFrame(master, text="Visualization")
        canvasFrame.grid(row=0,column=1,sticky='nesw',rowspan=2)
        ph_labelCanvas = ttk.Label(canvasFrame, text='Canvas')
        ph_labelCanvas.grid()


    def onCreateRobotButtonPress(self, var, mode, index):
        pass

    def onTargetVelxChange(self, var, mode, index):
        self.kinematicsAndPlotUpdate()

    def onTargetVelyChange(self, var, mode, index):
        self.kinematicsAndPlotUpdate()

    def onTargetHeightChange(self, var, mode, index):
        self.kinematicsAndPlotUpdate()

    def kinematicsAndPlotUpdate(self):
        print(f"New target: v=[{self.target_velx.get():.2f}, {self.target_vely.get():.2f}], h={self.target_height.get():.2f}")
        pass

    def velxScaleUpdate(self, value):
        self.target_velx.set(value)

    def velyScaleUpdate(self, value):
        self.target_vely.set(value)

    def heightScaleUpdate(self, value):
        self.target_height.set(value)




if __name__ == '__main__':
    myApp = RobotApp(theme='arc')
    myApp.mainloop()