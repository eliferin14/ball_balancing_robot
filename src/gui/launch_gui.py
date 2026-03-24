import sys
import os

# Ensure the 'src' directory is in the python path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from robot_kinematics.robot3RRS import robot3RRS
from gui.application import RobotApp

if __name__ == "__main__":
    robot = robot3RRS(baseDistance=50, armLength=50, forearmLength=60, platDistance=40)

    myApp = RobotApp(theme='arc')
    myApp.mainloop()