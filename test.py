from kinematics.robot3RRS import robot3RRS
from gui.application import RobotApp

robot = robot3RRS(baseDistance=50, armLength=50, forearmLength=60, platDistance=40)

myApp = RobotApp(theme='arc')
myApp.mainloop()