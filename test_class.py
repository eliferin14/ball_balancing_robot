from kinematics.robot3RRS import robot3RRS
from kinematics.inverse_kinematics_old import *
from spatialmath.base import *
from spatialmath import SO3, SE3
import matplotlib.pyplot as plt
import argparse

# Initialise plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Drawing functions
def pointPlot(point, ax, color='red'):
    ax.scatter(point[0], point[1], point[2], color=color)

def pointsPlot(points, ax, color='red'):
    for p in points:
        pointPlot(p,ax,color)

def drawSegmentsOpen(vertices, plt, color='k'):
    for i in range(1,len(vertices)):
        plt.plot([vertices[i-1,0],vertices[i,0]], [vertices[i-1,1],vertices[i,1]], [vertices[i-1,2],vertices[i,2]], color = color)

def drawSegmentsClosed(vertices, plt, color='k'):
    drawSegmentsOpen(vertices, plt, color)
    plt.plot([vertices[0,0],vertices[-1,0]], [vertices[0,1],vertices[-1,1]], [vertices[0,2],vertices[-1,2]], color = color)

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument("-vx", help="Velocity vector [x]", default=0)
parser.add_argument("-vy", help="Velocity vector [y]", default=0)
parser.add_argument("-ht", help="Platform height", default=40)
args = parser.parse_args()
print(f"Received arguments: {args}")

velx = float(args.vx)
vely = float(args.vy)
targetHeight = float(args.ht)
print([velx, vely])




robot = robot3RRS(40, 50, 40, 40)

print("-----------------------------------")
normal = velocityVector2normal(velx, vely)
print("-----------------------------------")

baseTriangle = robot.getBaseTriangle()
#yaw, pitch = robot.getYawPitchFromNormal(normal)
#R = robot.getRotationMatrixFromYawPitch(yaw, pitch)
#R = robot.getRotationMatrixFromNormal(normal)
#print(R)
#platOrigin = robot.getPlatformOrigin(R.R, 0)
#print(platOrigin)
#platTriang = robot.computePlatformTriangle(R.R, platOrigin)
#print(f"triangle: {platTriang}")


robot.inverseKinematics(targetHeight, normal)
armA = robot.getArmPoints('A')
armB = robot.getArmPoints('B')
armC = robot.getArmPoints('C')
platTriangle = robot.getPlatformTriangle()



T_w2A = SE3(0,0,0)
T_w2A.plot()
drawSegmentsClosed(baseTriangle.T, plt, 'gray')
drawSegmentsClosed(platTriangle.T, plt)
drawSegmentsOpen(armA.T, plt, 'red')
drawSegmentsOpen(armB.T, plt, 'green')
drawSegmentsOpen(armC.T, plt, 'blue')
robot.T.plot(length=20)


plt.axis('equal')
plt.show()