import unittest
import numpy as np
from robot_kinematics.robot3RRS import robot3RRS

class TestKinematicsConsistency(unittest.TestCase):
    def setUp(self):
        # Initialize robot with standard parameters
        self.robot = robot3RRS(baseDistance=50, armLength=50, forearmLength=60, platDistance=40)

    def test_dk_after_ik(self):
        """Tests that IK followed by DK returns the original platform pose."""
        # Define target pose
        vx_target, vy_target, h_target = 0.1, -0.05, 55.0
        
        # 1. Compute IK
        theta1, theta2, theta3 = self.robot.inverseKinematics(vx_target, vy_target, h_target)
        
        # 2. Compute DK from these angles
        vx_res, vy_res, h_res = self.robot.directKinematics(theta1, theta2, theta3)
        
        # 3. Assert results match target within tolerance
        self.assertAlmostEqual(vx_target, vx_res, places=4)
        self.assertAlmostEqual(vy_target, vy_res, places=4)
        self.assertAlmostEqual(h_target, h_res, places=4)

    def test_ik_after_dk(self):
        """Tests that DK followed by IK returns the original joint angles."""
        # Start from a reachable platform pose to get a valid set of angles
        vx_init, vy_init, h_init = 0.0, 0.0, 50.0
        t1_start, t2_start, t3_start = self.robot.inverseKinematics(vx_init, vy_init, h_init)
        
        # 1. Compute DK from these joint angles
        vx, vy, h = self.robot.directKinematics(t1_start, t2_start, t3_start)
        
        # 2. Compute IK from resulting pose
        t1_res, t2_res, t3_res = self.robot.inverseKinematics(vx, vy, h)
        
        # 3. Assert results match starting angles
        self.assertAlmostEqual(t1_start, t1_res, places=4)
        self.assertAlmostEqual(t2_start, t2_res, places=4)
        self.assertAlmostEqual(t3_start, t3_res, places=4)

if __name__ == '__main__':
    unittest.main()
