import math
import numpy as np
import spatialmath as sm
import spatialmath.base as smb

SQRT_3 = math.sqrt(3)

class robot3RRS:
    """
    Mathematical description of a 3RRS parallel robot.
    This class handles the core kinematics calculations independent of hardware or simulation.
    """

    def __init__(self, baseDistance, armLength, forearmLength, platDistance, 
                 alpha12=2/3*np.pi, alpha13=-2/3*np.pi, 
                 alpha45=2/3*np.pi, alpha46=-2/3*np.pi, 
                 maxTilt=0.7) -> None:
        
        self.b = baseDistance
        self.a = armLength
        self.f = forearmLength
        self.p = platDistance

        # Angles defining the positions of the joints on the base and platform
        self.alpha12 = alpha12
        self.alpha13 = alpha13
        self.alpha45 = alpha45
        self.alpha46 = alpha46

        self.maxTilt = maxTilt

        # Define base triangle vertices in world coordinates
        self.O01 = smb.colvec([self.b, 0, 0])
        self.O02 = smb.colvec([-self.b/2, SQRT_3/2*self.b, 0])
        self.O03 = smb.colvec([-self.b/2, -SQRT_3/2*self.b, 0])

        # Current state variables
        self.theta1, self.phi1, self.O14 = 0, 0, None
        self.theta2, self.phi2, self.O25 = 0, 0, None
        self.theta3, self.phi3, self.O36 = 0, 0, None
        
        self.O7 = None # Platform origin
        self.platTransform = sm.SE3()
        self.O74, self.O75, self.O76 = None, None, None # Platform vertices

    def computeElbowPosition(self, theta, alpha):
        """Calculates the elbow position in world coordinates for a given shoulder angle and leg orientation."""
        Rz = smb.rotz(alpha)
        elbow_local = smb.colvec([self.b + self.a * np.cos(theta), 0, self.a * np.sin(theta)])
        return Rz @ elbow_local

    def directKinematics(self, theta1, theta2, theta3):
        """
        Calculates the platform pose (vel_x, vel_y, height) given the active joint angles.
        Uses numerical optimization to find the pose that satisfies leg length constraints.
        """
        from scipy.optimize import fsolve
        
        # Calculate fixed elbow positions based on input angles
        O14 = self.computeElbowPosition(theta1, 0)
        O25 = self.computeElbowPosition(theta2, self.alpha12)
        O36 = self.computeElbowPosition(theta3, self.alpha13)
        elbows = [O14, O25, O36]

        def equations(q):
            yaw, pitch, H = q
            # Generate rotation and origin from current guess
            R_obj = self.computeRotationMatrixFromYawPitch(yaw, pitch)
            R = R_obj.R
            O7 = self.computePlatformOrigin(R, H)
            plat_vertices = self.computePlatformTriangle(R, O7)
            
            # Constraint: distance from elbow to platform joint must be 'f'
            residuals = []
            for i in range(3):
                dist_sq = np.sum((plat_vertices[:, i:i+1] - elbows[i])**2)
                residuals.append(dist_sq - self.f**2)
            return residuals

        # Initial guess: neutral horizontal position at forearm height
        initial_guess = [0, 0, self.f]
        
        sol, info, ier, msg = fsolve(equations, initial_guess, full_output=True)
        
        if ier != 1:
            raise RuntimeError(f"Direct kinematics failed to converge: {msg}")
            
        yaw, pitch, H = sol
        
        # Map yaw/pitch back to vel_x/vel_y (acceleration target representation)
        tan_p = math.tan(pitch)
        tan_y = math.tan(yaw)
        nz = 1.0 / math.sqrt(tan_p**2 + tan_y**2 + 1)
        nx = nz * tan_p
        ny = nz * tan_y
        
        vel_x = nx
        vel_y = -ny
        
        return vel_x, vel_y, H

    def inverseKinematics(self, vel_x, vel_y, platHeight):
        """
        Calculates the joint angles required to achieve a specific platform tilt and height.
        vel_x, vel_y: represents the tilt (acceleration vector analogy)
        platHeight: vertical distance from base to platform center
        """
        platNormal = self.computeNormalFromTargetVelocity(vel_x, vel_y)
        yaw, pitch = self.computeYawPitchFromNormal(platNormal)
        platRotation = self.computeRotationMatrixFromYawPitch(yaw, pitch)
        
        self.O7 = self.computePlatformOrigin(platRotation.R, platHeight)
        self.platTransform = sm.SE3.Rt(platRotation.R, self.O7)
        
        # Calculate platform vertices in world coordinates
        platTriangle = self.computePlatformTriangle(platRotation.R, self.O7)
        self.O74, self.O75, self.O76 = platTriangle[:,0:1], platTriangle[:,1:2], platTriangle[:,2:3]

        # Apply inverse kinematics to all three 2R legs
        # Arm 1 (aligned with X axis)
        self.theta1, self.phi1, self.O14 = self.invKin2R(self.O74, 0) 

        # Arm 2 (rotated by alpha12)
        self.theta2, self.phi2, self.O25 = self.invKin2R(self.O75, self.alpha12)

        # Arm 3 (rotated by alpha13)
        self.theta3, self.phi3, self.O36 = self.invKin2R(self.O76, self.alpha13)
        
        return (self.theta1, self.theta2, self.theta3)

    def computeNormalFromTargetVelocity(self, vel_x=0.5, vel_y=0):
        vel_norm_squared = vel_x**2 + vel_y**2
        if vel_norm_squared >= 1:
            raise ValueError(f"Norm of velocity vector {np.sqrt(vel_norm_squared)} is greater or equal to 1. Impossible tilt.")

        normalVector = np.zeros((3,))
        normalVector[0] = vel_x
        normalVector[1] = -vel_y
        normalVector[2] = np.sqrt(1 - vel_norm_squared)

        return normalVector

    def computeRotationMatrixFromYawPitch(self, yaw=0, pitch=0):
        # roll calculation to maintain constraint (often specific to 3RRS geometry)
        # roll = math.atan( -math.sin(yaw)*math.sin(pitch) / ( math.cos(yaw)+math.cos(pitch) ) )
        # Using spatialmath RPY (Roll-Pitch-Yaw) with 'xyz' order
        # Note: roll is derived from yaw/pitch to satisfy the 3RRS mechanical constraints
        denom = math.cos(yaw) + math.cos(pitch)
        if abs(denom) < 1e-9:
            roll = 0 # Singular configuration
        else:
            roll = math.atan(-math.sin(yaw) * math.sin(pitch) / denom)
            
        return sm.SO3.RPY([roll, pitch, yaw], order='xyz')
    
    def computeYawPitchFromNormal(self, normal):
        yaw = np.arctan2(normal[1], normal[2])
        pitch = np.arctan2(normal[0], normal[2])
        return yaw, pitch

    def computePlatformOrigin(self, R, O7_z):
        # Extract components of the rotation matrix to solve for X and Y position
        # This is specific to the 3RRS kinematics model where X and Y are constrained by tilt
        ux = R[0, 0]
        uy = R[1, 0]
        vy = R[1, 1]

        # Geometric constraints of the 3RRS structure
        O7_x = self.p * (ux - vy) / 2
        O7_y = -uy * self.p

        return smb.colvec([O7_x, O7_y, O7_z])

    def computePlatformTriangle(self, R, O7):
        pvec = smb.colvec([self.p, 0, 0])
    
        # Vertex 4
        v4 = O7 + smb.colvec(R @ pvec)

        # Vertex 5
        Rz_45 = sm.SO3.Rz(self.alpha45).R
        v5 = O7 + smb.colvec(R @ Rz_45 @ pvec)

        # Vertex 6
        Rz_46 = sm.SO3.Rz(self.alpha46).R
        v6 = O7 + smb.colvec(R @ Rz_46 @ pvec)

        return np.hstack([v4, v5, v6])

    def invKin2R(self, O7j, alpha1i):
        """
        Inverse kinematics for a single 2R leg in 3D space.
        O7j: Target platform joint position in world coordinates.
        alpha1i: Angle of the leg's plane relative to world XZ plane.
        """
        # 1. Rotate the point so that the leg lies in the XZ plane
        Rz_i1 = smb.rotz(-alpha1i)
        Rz_1i = smb.rotz(alpha1i)
        P = Rz_i1 @ O7j

        # 2. Translate so the base joint is at the origin of this local 2D frame
        P -= smb.colvec([self.b, 0, 0])

        Px, Pz = P[0, 0], P[2, 0]

        # 3. Solve 2D IK for the two links (a and f)
        # law of cosines for the elbow angle
        k = (self.a**2 + self.f**2 - Px**2 - Pz**2) / (2 * self.a * self.f)
        
        if abs(k) > 1:
            raise ValueError(f"Target position {O7j.flatten()} is out of reach for arm at alpha={alpha1i}")
            
        alpha = np.arccos(k)
        phi = np.pi - alpha # elbow angle
        
        beta = np.arctan2(self.f * np.sin(phi), self.a + self.f * np.cos(phi))
        gamma = np.arctan2(Pz, Px)
        theta = gamma - beta # shoulder angle

        # Calculate the elbow point in world coordinates
        elbow_local = smb.colvec([self.b + self.a * np.cos(theta), 0, self.a * np.sin(theta)])
        Oij = Rz_1i @ elbow_local

        return theta, phi, Oij
    
    # Helper methods for visualization / data retrieval
    def getArmPoints(self, armIndex=0):
        if armIndex == 0 or armIndex == 'A':
            return np.hstack([self.O01, self.O14, self.O74])
        elif armIndex == 1 or armIndex == 'B':
            return np.hstack([self.O02, self.O25, self.O75])
        elif armIndex == 2 or armIndex == 'C':
            return np.hstack([self.O03, self.O36, self.O76])
        else:
            raise ValueError("Invalid arm index")

    def getBaseTriangle(self):
        return np.hstack([self.O01, self.O02, self.O03])

    def getPlatformTriangle(self):
        return np.hstack([self.O74, self.O75, self.O76])
