from kinematics.robot_geometry import *
from spatialmath.base import *

def directkinematics2R(theta, phi):
    A = colvec([BASE_TRIANGLE_DIAMETER/2,0,0])
    B = A + colvec([ARM_LENGTH*np.cos(theta), 0, ARM_LENGTH*np.sin(theta)])
    C = B + colvec([FOREARM_LENGTH*np.cos(theta+phi), 0, FOREARM_LENGTH*np.sin(theta+phi)])

    return np.hstack([A,B,C])
