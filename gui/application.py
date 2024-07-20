import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk

from kinematics.robot3RRS import robot3RRS
from graphicsUtils.drawingFunctions import *

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt

import numpy as np

class RobotApp(ThemedTk):
    def __init__(self, *args, **kwargs):
        ThemedTk.__init__(self, *args, **kwargs)

        # Define an event to close the window
        self.bind('<Escape>', lambda e: self.closeWindow(e))
        self.bind('<q>', lambda e: self.closeWindow(e))

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

    def closeWindow(self, e):
        self.destroy()  
        exit()

    def createRobotCreationFrame(self, master):
        robotCreationFrame = ttk.LabelFrame(master, text="Robot parameters")
        robotCreationFrame.grid(row=0,column=0,sticky='nesw')
        ph_labelParameters = ttk.Label(robotCreationFrame, text='Parameters')
        ph_labelParameters.grid()

        self.robot = robot3RRS(self.baseRadius.get(), self.armLength.get(), self.forearmLength.get(), self.platRadius.get())

    def createTargetSelectionFrame(self, master):        
        targetSelectionFrame = ttk.LabelFrame(master, text="Target")
        targetSelectionFrame.grid(row=1,column=0,sticky='nesw')

        velxSlider = ttk.Scale(targetSelectionFrame, from_=-1, to=1, orient='horizontal', command=self.velxScaleUpdate)
        velxSlider.grid()

        velySlider = ttk.Scale(targetSelectionFrame, from_=-1, to=1, orient='horizontal', command=self.velyScaleUpdate)
        velySlider.grid()
        
        heightSlider = ttk.Scale(targetSelectionFrame, from_=0, to=100, value=self.robot.f, orient='horizontal', command=self.heightScaleUpdate)
        heightSlider.grid()

    def createCanvasFrame(self, master):
        canvasFrame = ttk.LabelFrame(master, text="Visualization")
        canvasFrame.grid(row=0,column=1,sticky='nesw',rowspan=2)

        # Define the figure and axis
        self.robotFig = plt.figure(figsize=(8,8), dpi=100)
        self.robotAx = self.robotFig.add_subplot(111, projection='3d')

        # Create the canvas
        self.canvas = FigureCanvasTkAgg(self.robotFig, canvasFrame)
        self.canvas.get_tk_widget().grid()
        self.drawRobot()

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

        self.robotKinematics()
        self.drawRobot()
        
    def robotKinematics(self):
        self.robot.inverseKinematics(self.target_velx.get(), self.target_vely.get(), self.target_height.get())

    def drawRobot(self):
        # Clear the plot
        self.robotAx.cla()

        # Get all the needed data
        baseTriangle = self.robot.getBaseTriangle()
        platformTriangle = self.robot.getPlatformTriangle()
        armA = self.robot.getArmPoints('A')
        armB = self.robot.getArmPoints('B')
        armC = self.robot.getArmPoints('C')
        platRF = self.robot.platTransform

        # Draw the robot
        drawSegmentsClosed(baseTriangle, self.robotAx, marker='o')
        drawSegmentsClosed(platformTriangle, self.robotAx, color='k', marker='o')
        drawSegmentsOpen(armA, self.robotAx, color='red', marker='o')
        drawSegmentsOpen(armB, self.robotAx, color='green', marker='o')
        drawSegmentsOpen(armC, self.robotAx, color='blue', marker='o')
        platRF.plot(length=self.robot.p/3, color='k')

        # Define axes limits
        xmax = (self.robot.b + self.robot.a) * 1.2
        ymax = np.sqrt(3)/2 * xmax
        zmax = (self.robot.a + self.robot.f) * 1.05
        zmin = 0 # -self.robot.a * 1.05
        self.robotAx.set_xlim([-0.7*xmax, xmax])
        self.robotAx.set_ylim([-ymax, ymax])
        self.robotAx.set_zlim([zmin, zmax])

        # Draw the plot in the widget
        self.canvas.draw()

    def velxScaleUpdate(self, value):
        self.target_velx.set(value)

    def velyScaleUpdate(self, value):
        self.target_vely.set(value)

    def heightScaleUpdate(self, value):
        self.target_height.set(value)




if __name__ == '__main__':
    myApp = RobotApp(theme='arc')
    myApp.mainloop()