import math
from spatialmath import *
from spatialmath.geom3d import *

SQRT_3 = math.sqrt(3)

ARM_LENGTH = 50
FOREARM_LENGTH = 80
BASE_TRIANGLE_DIAMETER = 150
PLATFORM_TRIANGLE_DIAMETER = 120

BASE_TRIANGLE_SIDELENGTH = SQRT_3 / 2 * BASE_TRIANGLE_DIAMETER
PLATFORM_TRIANGLE_SIDELENGTH = SQRT_3 / 2 * PLATFORM_TRIANGLE_DIAMETER

# Define fixed reference frames
T_w2A = SE3(0,0,0)
T_w2B = SE3.Rz(120, unit='deg')
T_w2C = SE3.Rz(-120, unit='deg')

# Define XY, XZ, YZ planes
planeXY = Plane3.PointNormal([0,0,0],[0,0,1])
planeXZ = Plane3.PointNormal([0,0,0],[0,1,0])
planeYZ = Plane3.PointNormal([0,0,0],[1,0,0])

# Define A,B,C planes 
planeA = Plane3.PointNormal([0,0,0], [0,1,0])
planeB = Plane3.PointNormal([0,0,0], [-SQRT_3/2,-1/2,0])
planeC = Plane3.PointNormal([0,0,0], [SQRT_3/2,-1/2,0])

# Define vertices of the base triangle
baseA = np.array([0,0,0])

