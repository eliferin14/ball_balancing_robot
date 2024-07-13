#from kinematics.inverse_kinematics import *
from kinematics.robot_geometry    import *
from kinematics.direct_kinematics import *
from spatialmath.base import *
from spatialmath.geom3d import Line3
import matplotlib.pyplot as plt

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

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
#ax.set_xlim(-10,10)
#ax.set_ylim(-10,10)
#ax.set_zlim(-10,10)

""" trplot( transl(0,0,0), frame='W', rviz=True, width=1, ax=ax)

assert planeA.contains([10,0,5])
assert planeB.contains([-1,SQRT_3,4])
assert planeC.contains([-1,-SQRT_3,-2])

h = 10
platNormal = velocityVector2normal(0.5,0.5)
platPlane = Plane3.PointNormal([0,0,h],platNormal)
#platPlane.plot(ax=ax)
print(platPlane)

# intersect planes to find lines where the vertices lie
vertexA_line = Line3.TwoPlanes(planeA, platPlane)
vertexB_line = Line3.TwoPlanes(planeB, platPlane)
vertexC_line = Line3.TwoPlanes(planeC, platPlane)
#print(vertexA_line.pp)
#print(vertexA_line.ppd)
#print(vertexA_line.uw)
#print(vertexB_line)
#print(vertexC_line)

lineA_int_planeYZ, _ = vertexA_line.intersect_plane(planeYZ)
#pointPlot(lineA_int_planeYZ, ax)
vertexA_line2 = Line3.PointDir(lineA_int_planeYZ, vertexA_line.uw)
print(vertexA_line)
print(vertexA_line2)
print(vertexA_line.lam(lineA_int_planeYZ))
print(vertexA_line2.lam(lineA_int_planeYZ))
vertexA_line.plot(ax=ax)
vertexA_line2.plot(ax=ax)

#ax.scatter(vertexA_line.pp[0],vertexA_line.pp[1],vertexA_line.pp[2])
#vertexB_line.plot(ax=ax)
#vertexC_line.plot(ax=ax) """

T_w2A.plot(color='red')
T_w2B.plot(color='green')
T_w2C.plot(color='blue')

""" PA = np.array([5,0,3])
PB = T_w2B * PA
PC = T_w2C * PA

pointPlot(PA, ax, 'cyan')
pointPlot(PB, ax, 'cyan')
pointPlot(PC, ax, 'cyan') """

armA_points = ( T_w2A * directkinematics2R(np.pi/4, np.pi/3) ).T
armB_points = ( T_w2B * directkinematics2R(np.pi/4, np.pi/4) ).T
armC_points = ( T_w2C * directkinematics2R(np.pi/3, np.pi/3) ).T
pointsPlot(armA_points, ax, 'red')
pointsPlot(armB_points, ax, 'green')
pointsPlot(armC_points, ax, 'blue')
print(armA_points)
print(armB_points)
print(armC_points)

drawSegmentsOpen(armA_points, plt, 'red')
drawSegmentsOpen(armB_points, plt, 'green')
drawSegmentsOpen(armC_points, plt, 'blue')

print(type(armA_points))
baseTriangleVertices = np.vstack([ armA_points[0], armB_points[0], armC_points[0] ])
platTriangleVertices = np.vstack([ armA_points[2], armB_points[2], armC_points[2] ])
print(baseTriangleVertices)
drawSegmentsClosed(baseTriangleVertices, plt, 'gray')
drawSegmentsClosed(platTriangleVertices, plt, 'black')

plt.axis('equal')
plt.show()
