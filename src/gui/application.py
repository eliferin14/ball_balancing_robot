import tkinter as tk
from tkinter import ttk
from ttkthemes import ThemedTk

from .kinematics.robot3RRS import robot3RRS
from .graphicsUtils.drawingFunctions import *

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

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
        self.mainFrame = ttk.Frame(self, height=720, width=1080, padding=10)
        self.mainFrame.grid(row=0,column=0,sticky='nesw')

        # Robot parameters variables
        self.baseRadius = tk.DoubleVar(self, value=50)
        self.platRadius = tk.DoubleVar(self, value=40)
        self.armLength = tk.DoubleVar(self, value=40)
        self.forearmLength = tk.DoubleVar(self, value=60)

        # Target variables
        self.target_accx = tk.DoubleVar(self, value=0)
        self.target_accy = tk.DoubleVar(self, value=0)
        self.target_height = tk.DoubleVar(self, value=50)
        self.target_accx.trace_add('write', self.onTargetAccxChange)
        self.target_accy.trace_add('write', self.onTargetAccyChange)
        self.target_height.trace_add('write', self.onTargetHeightChange)

        # init event variable
        self.mousePressed = False

        # Declare robot creation frame
        self.createRobotCreationFrame(self.mainFrame)

        # Declare target selection frame
        self.createTargetSelectionFrame(self.mainFrame)

        # Declare canvas frame
        self.createCanvasFrame(self.mainFrame)

    def closeWindow(self, e):
        self.destroy()  
        exit()

    def createRobotCreationFrame(self, master):
        robotCreationFrame = ttk.LabelFrame(master, text="Robot parameters")
        robotCreationFrame.grid(row=0,column=0,sticky='nesw')
        robotCreationFrame.columnconfigure([0,1],weight=1)

        base_labelParameters = ttk.Label(robotCreationFrame, text='Base radius')
        base_labelParameters.grid(sticky='w')
        baseEntry = ttk.Entry(robotCreationFrame, textvariable=self.baseRadius)
        baseEntry.grid(row=0, column=1, sticky='e')

        plat_labelParameters = ttk.Label(robotCreationFrame, text='Platform radius')
        plat_labelParameters.grid(sticky='w')
        platEntry = ttk.Entry(robotCreationFrame, textvariable=self.platRadius)
        platEntry.grid(row=1, column=1, sticky='e')

        arm_labelParameters = ttk.Label(robotCreationFrame, text='Arm length')
        arm_labelParameters.grid(sticky='w')
        armEntry = ttk.Entry(robotCreationFrame, textvariable=self.armLength)
        armEntry.grid(row=2, column=1, sticky='e')

        forearm_labelParameters = ttk.Label(robotCreationFrame, text='Forearm length')
        forearm_labelParameters.grid(sticky='w')
        forearmEntry = ttk.Entry(robotCreationFrame, textvariable=self.forearmLength)
        forearmEntry.grid(row=3, column=1, sticky='e')

        createRobotButton = ttk.Button(robotCreationFrame, text="Create robot", command=self.onCreateRobotButtonPress)
        createRobotButton.grid(columnspan=2)

        self.createRobot()

    def createTargetSelectionFrame(self, master):        
        targetSelectionFrame = ttk.LabelFrame(master, text="Target")
        targetSelectionFrame.grid(row=1,column=0,sticky='nesw')

        # Accx selector
        accxLabel = ttk.Label(targetSelectionFrame, text="Acceleration along X")
        accxLabel.grid(row=0,column=0)

        accxSlider = ttk.Scale(targetSelectionFrame, from_=-self.robot.maxTilt, to=self.robot.maxTilt, orient='horizontal', command=self.accxScaleUpdate)
        accxSlider.grid(row=0,column=1)

        # Accy selector
        accyLabel = ttk.Label(targetSelectionFrame, text='Acceleration along Y')
        accyLabel.grid(row=1,column=0)

        accySlider = ttk.Scale(targetSelectionFrame, from_=-self.robot.maxTilt, to=self.robot.maxTilt, orient='horizontal', command=self.accyScaleUpdate)
        accySlider.grid(row=1,column=1)
        
        # Height selector
        heightLabel = ttk.Label(targetSelectionFrame, text='Platform height')
        heightLabel.grid(row=2,column=0)

        heightSlider = ttk.Scale(targetSelectionFrame, from_=0, to=(self.robot.a+self.robot.f)*0.99, value=self.robot.f, orient='horizontal', command=self.heightScaleUpdate)
        heightSlider.grid(row=2,column=1)

        # Define the figure and the axis
        self.targetFig = plt.figure(figsize=(3,3), dpi=100)
        self.targetAx = self.targetFig.add_subplot()

        # Create the canvas
        self.targetCanvas = FigureCanvasTkAgg(self.targetFig, targetSelectionFrame)
        self.targetCanvas.get_tk_widget().grid(columnspan=2)
        cid = self.targetFig.canvas.mpl_connect('button_press_event', self.onTargetCanvasPress)
        cid = self.targetFig.canvas.mpl_connect('button_release_event', self.onTargetCanvasRelease)
        cid = self.targetFig.canvas.mpl_connect('motion_notify_event', self.onTargetCanvasDrag)
        self.drawTarget()

    def createCanvasFrame(self, master):
        canvasFrame = ttk.LabelFrame(master, text="Visualization")
        canvasFrame.grid(row=0,column=1,sticky='nesw',rowspan=2)

        # Define the figure and axis
        self.robotFig = plt.figure(figsize=(8,8), dpi=100)
        self.robotAx = self.robotFig.add_subplot(111, projection='3d')

        # Create the canvas
        self.robotCanvas = FigureCanvasTkAgg(self.robotFig, canvasFrame)
        self.robotCanvas.get_tk_widget().grid()
        self.drawRobot()

    def onCreateRobotButtonPress(self):
        print(f"Base radius: {self.baseRadius.get()}")
        print(f"Platform radius: {self.platRadius.get()}")
        print(f"Arm length: {self.armLength.get()}")
        print(f"Forearm length: {self.forearmLength.get()}")

        self.createRobot()
        self.createTargetSelectionFrame(self.mainFrame)
        self.drawRobot()
    
    def createRobot(self):
        self.robot = robot3RRS(self.baseRadius.get(), self.armLength.get(), self.forearmLength.get(), self.platRadius.get())

    def onTargetAccxChange(self, var, mode, index):
        self.onTargetChange()

    def onTargetAccyChange(self, var, mode, index):
        self.onTargetChange()

    def onTargetHeightChange(self, var, mode, index):
        self.onTargetChange()

    def onTargetCanvasPress(self, event):
        self.mousePressed = True
        cx, cy = event.xdata, event.ydata
        #print(f"Click: [{cx:.2f},{cy:.2f}]")
        self.target_accx.set(cx)
        self.target_accy.set(cy)

    def onTargetCanvasRelease(self, event):
        self.mousePressed = False

    def onTargetCanvasDrag(self, event):
        if not self.mousePressed:
            return
        cx, cy = event.xdata, event.ydata
        self.target_accx.set(cx)
        self.target_accy.set(cy)

    def onTargetChange(self):
        #print(f"New target: v=[{self.target_accx.get():.2f}, {self.target_accy.get():.2f}], h={self.target_height.get():.2f}")

        self.robotKinematics()
        self.drawTarget()
        self.drawRobot()
        
    def robotKinematics(self):
        self.robot.inverseKinematics(self.target_accx.get(), self.target_accy.get(), self.target_height.get())

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
        platRF.plot(length=self.robot.p/3, color='k')
        drawSegmentsClosed(baseTriangle, self.robotAx, marker='o')
        drawSegmentsOpen(armA, self.robotAx, color='red', marker='o')
        drawSegmentsOpen(armB, self.robotAx, color='green', marker='o')
        drawSegmentsOpen(armC, self.robotAx, color='blue', marker='o')
        drawSegmentsClosed(platformTriangle, self.robotAx, color='k', marker='o')
        #print(platRF)

        # Define axes limits
        xmax = (self.robot.b + self.robot.a) * 1.2
        ymax = np.sqrt(3)/2 * xmax
        zmax = (self.robot.a + self.robot.f) * 1.05
        zmin = 0 # -self.robot.a * 1.05
        self.robotAx.set_xlim([-0.7*xmax, xmax])
        self.robotAx.set_ylim([-ymax, ymax])
        self.robotAx.set_zlim([zmin, zmax])

        # Draw the plot in the widget
        self.robotCanvas.draw()

    def drawTarget(self):
        # Clear the plot
        self.targetAx.cla()

        # Draw the limit circle
        limitCircle = plt.Circle((0,0), self.robot.maxTilt, fill=False, color='gray')
        self.targetAx.add_artist(limitCircle)

        # Draw the arrowcorresponding to target acceleration
        self.targetAx.arrow(0, 0, self.target_accx.get(), self.target_accy.get(), width=0.015, color='k')

        # Set axes limits
        self.targetAx.set_xlim(-1,1)
        self.targetAx.set_ylim(-1,1)

        # Draw the plot in the widget
        self.targetCanvas.draw()

    def accxScaleUpdate(self, value):
        self.target_accx.set(value)

    def accyScaleUpdate(self, value):
        self.target_accy.set(value)

    def heightScaleUpdate(self, value):
        self.target_height.set(value)




if __name__ == '__main__':
    myApp = RobotApp(theme='yaru')
    myApp.mainloop()