import numpy as np
from spatialmath import SE3

# Physical Robot Dimensions (all units in mm unless specified)
ARM_LENGTH = 50
FOREARM_LENGTH = 80
BASE_TRIANGLE_DIAMETER = 150
PLATFORM_TRIANGLE_DIAMETER = 120

# Derived Geometric Constants
SQRT_3 = np.sqrt(3)
BASE_TRIANGLE_SIDELENGTH = SQRT_3 / 2 * BASE_TRIANGLE_DIAMETER
PLATFORM_TRIANGLE_SIDELENGTH = SQRT_3 / 2 * PLATFORM_TRIANGLE_DIAMETER

# Leg angles relative to base center (for calculation)
ALPHA_1 = 0
ALPHA_2 = 2/3 * np.pi
ALPHA_3 = -2/3 * np.pi

# Fixed Reference Frames for each leg base
T_W2A = SE3(0, 0, 0)
T_W2B = SE3.Rz(120, unit='deg')
T_W2C = SE3.Rz(-120, unit='deg')
