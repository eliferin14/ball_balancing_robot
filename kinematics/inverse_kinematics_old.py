import math
import numpy as np
import transformations as tf
from spatialmath.geom3d import *

SQRT_3 = np.sqrt(3)

# Define XY, XZ, YZ planes
planeXY = Plane3.PointNormal([0,0,0],[0,0,1])
planeXZ = Plane3.PointNormal([0,0,0],[0,1,0])
planeYZ = Plane3.PointNormal([0,0,0],[1,0,0])

# Define A,B,C planes 
planeA = Plane3.PointNormal([0,0,0], [0,1,0])
planeB = Plane3.PointNormal([0,0,0], [-SQRT_3/2,-1/2,0])
planeC = Plane3.PointNormal([0,0,0], [SQRT_3/2,-1/2,0])




# Given the velocity vector calculate the z component and return the normal vector describing the target platform plane
def velocityVector2normal(vel_x=0.5, vel_y=0):
    normalVector = np.zeros((3,))

    vel_norm_squared = vel_x**2 + vel_y**2
    # The norm of the velocity vector must be < 1
    if vel_norm_squared >= 1:
        print("Norm of velocity vector greater or equal to 1")
        exit()

    normalVector[0] = vel_x
    normalVector[1] = -vel_y
    normalVector[2] = np.sqrt( 1 - vel_norm_squared )

    return normalVector

# Given the normal vector of the platform plane, calculate the rotation matrix of the platform RF wrt world reference frame
def normal2platformRotationMatrix(normal=[0.5,0,SQRT_3/2]):
    rotMatrix = np.zeros((3,3))

    # z is trivial: it is the same as the normal
    rotMatrix[:,2] = normal

    # x is the result of 3 conditions:
    x_p = np.zeros((3,))
    # 1: x is always in the A plane => its y component is 0
    # 2: x is orthogonal to z (and the normal) => their scalar product is 0
    # 3: x is a unit vector => its norm must be 0
    k = 1 + (normal[0]**2/normal[2]**2)
    x_p[0] = 1 / np.sqrt(k)
    x_p[2] = -normal[0]/normal[2] * x_p[0]
    rotMatrix[:,0] = x_p

    # y is obtained with the vector product of z and x (right hand rule)
    rotMatrix[:,1] = np.cross(normal, x_p)

    #print(rotMatrix)

    return rotMatrix

# Given the side length of the triangle, get the coordinates of the vertices in the platform RF
def getTriangleVertices(sidelength):
    A,B,C = np.zeros((3,))

    A[0] = 1 / SQRT_3 * sidelength

    B[0] = -1 / (2*SQRT_3) * sidelength
    B[1] = 1/2 * sidelength

    C[0] = -1 / (2*SQRT_3) * sidelength
    C[1] = -1/2 * sidelength

    return A,B,C

# Given the rotation matrix, the sidelength of the triangle and the target height, 
# calculate the translation vector between world origin and platform RF origin
def rotVerticesHeight2transVector(R, l, h):
    tVec = np.zeros((3,))

    tVec[1] = -1/SQRT_3 * R[1,0] * l

    alpha1 = ( 1/(2*SQRT_3)*(R[0,0]-R[1,1]) + 1/2*(+R[1,0]-R[0,1]) ) * l
    alpha2 = ( 1/(2*SQRT_3)*(R[0,0]-R[1,1]) + 1/2*(-R[1,0]+R[0,1]) ) * l
    print(f"alpha1: {alpha1}")
    print(f"alpha1: {alpha2}")

    #print(tVec)

    return tVec

# Given two planes described by normal and offset (combined in an homogeneous vector) return the intersecting line
def twoPlanes2intersectingLine(plane1, plane2):
    b = 0

if __name__ == '__main__':
    normal = velocityVector2normal(0.3,0.5)
    R_p2w = normal2platformRotationMatrix(normal)
    l = 5
    h = 10

    tVec = rotVerticesHeight2transVector(R_p2w,l,h)

    print(f"Rotation matrix: \n{R_p2w}")
    print(f"Translation vector: {tVec}")