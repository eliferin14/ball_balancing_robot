from kinematics.robot3RRS import robot3RRS
from kinematics.inverse_kinematics_old import *
from spatialmath.base import *
from spatialmath import SO3, SE3
import matplotlib.pyplot as plt

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

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




robot = robot3RRS(40, 50, 40, 40)

print("-----------------------------------")
normal = velocityVector2normal(0, 0.3)
print("-----------------------------------")

baseTriangle = robot.getBaseTriangle()
yaw, pitch = robot.getYawPitchFromNormal(normal)
R = robot.getRotationMatrixFromYawPitch(yaw, pitch)
#R = robot.getRotationMatrixFromNormal(normal)
print(R)
platOrigin = robot.getPlatformOrigin(R.R, 80)
print(platOrigin)
platTriang = robot.getPlatformTriangle(R.R, platOrigin)
print(f"triangle: {platTriang}")

#theta1, phi1, O14 = robot.invKin2R(platTriang[:,0])
#print([theta1, phi1, O14])
print(baseTriangle[:,0])
#arm1_points = np.hstack( [colvec(baseTriangle[:,0]), O14, colvec(platTriang[:,0])] )
#print(arm1_points)

print(robot.T)
robot.T.plot(length=20)

robot.inverseKinematics(80, normal)


T_w2A = SE3(0,0,0)
T_w2A.plot()
drawSegmentsClosed(baseTriangle.T, plt, 'gray')
drawSegmentsClosed(platTriang.T, plt)
#drawSegmentsOpen(arm1_points.T, plt, color='red')

plt.axis('equal')
plt.show()