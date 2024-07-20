import math
import numpy as np
from spatialmath.base import *
from spatialmath import *

SQRT_3 = math.sqrt(3)

class robot3RRS:

    def __init__(self, baseDistance, armLength, forearmLength, platDistance, alpha12=2/3*np.pi, alpha13=-2/3*np.pi, alpha45=2/3*np.pi, alpha46=-2/3*np.pi, maxTilt=0.7) -> None:
        self.b = baseDistance
        self.a = armLength
        self.f = forearmLength
        self.p = platDistance

        self.alpha12 = alpha12
        self.alpha13 = alpha13
        self.alpha45 = alpha45
        self.alpha46 = alpha46

        self.maxTilt = maxTilt

        # Define base triangle
        self.O01 = colvec([self.b, 0, 0])
        self.O02 = colvec([-self.b/2, SQRT_3/2*self.b, 0])
        self.O03 = colvec([-self.b/2, -SQRT_3/2*self.b, 0])

        # Initialize with default configuration
        self.inverseKinematics(0, 0, self.f)

    def directKinematics(self):
        pass

    def inverseKinematics(self, vel_x, vel_y, platHeight):
        platNormal = self.computeNormalFromTargetVelocity(vel_x, vel_y)
        yaw, pitch = self.computeYawPitchFromNormal(platNormal)
        platRotation = self.computeRotationMatrixFromYawPitch(yaw, pitch)
        platOrigin = self.computePlatformOrigin(platRotation.R, platHeight)
        platTriangle = self.computePlatformTriangle(platRotation.R, platOrigin)

        # Apply inverse kinematics to all three 2R robots
        
        # Arm 1
        self.theta1, self.phi1, self.O14 = self.invKin2R(self.O74, 0) 

        # Arm2
        self.theta2, self.phi2, self.O25 = self.invKin2R(self.O75, self.alpha12)

        # Arm3
        self.theta3, self.phi3, self.O36 = self.invKin2R(self.O76, self.alpha13)

    def computeNormalFromTargetVelocity(self, vel_x=0.5, vel_y=0):
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

    def computeRotationMatrixFromYawPitch(self, yaw=0, pitch=0):
        # Note: in this libray the rotations are about x y' z''
        roll = math.atan( -math.sin(yaw)*math.sin(pitch) / ( math.cos(yaw)+math.cos(pitch) ) )
        R = SO3.RPY([roll, pitch, yaw], order='xyz')
        return R
    
    def computeYawPitchFromNormal(self, normal):
        yaw = np.atan2(normal[1], normal[2])
        pitch = np.atan2(normal[0], normal[2])
        return yaw, pitch

    def computePlatformOrigin(self, R, O7_z):
        # Extract useful components of the rotation matrix
        ux = R[0][0]
        uy = R[1][0]
        vy = R[1][1]

        # Equation 3.11 
        O7_x = self.p * ( ux - vy ) / 2

        # Equation 3.7
        O7_y = -uy*self.p

        self.O7 = colvec([O7_x, O7_y, O7_z])

        self.platTransform = SE3.Rt(R, self.O7)

        return self.O7

    def computePlatformTriangle(self, R, O7):
        # Devine a vector [p,0,0]' as in equations 3.4, 3.5, 3.6
        pvec = colvec([self.p, 0, 0])
    
        # Equation 3.4
        self.O74 = O7 + colvec(R @ pvec)

        # Equation 3.5
        Rz_45 = SO3.Rz(self.alpha45).R
        self.O75 = O7 + colvec(R @ Rz_45 @ pvec)

        # Equation 3.6
        Rz_46 = SO3.Rz(self.alpha46).R
        self.O76 = O7 + colvec(R @ Rz_46 @ pvec)

        return np.hstack([self.O74, self.O75, self.O76])

    
    def invKin2R(self, O7j, alpha1i):

        # Rotate the point so that it is in the xz plane
        Rz_i1 = rotz(-alpha1i)
        Rz_1i = rotz(alpha1i)
        O7j = Rz_i1 @ O7j

        # Translate the point so that the base triangle vertex is in 0
        O7j -= colvec([self.b, 0, 0])

        assert( O7j[1,0] < 1e-9)
        #print(f"Rotated and translated O7j: {O7j}")

        O7jx, O7jz = O7j[0,0], O7j[2,0]
        #print(f"O7jx: {O7jx}")


        k = ( (self.a**2 + self.f**2 - O7jx**2 - O7jz**2) / (2*self.a*self.f) )
        #print(f"K: {k}")
        alpha = np.acos( k )
        #print(f"alpha: {alpha}")
        phi = np.pi - alpha
        beta = np.atan2( self.f*np.sin(phi), self.a+self.f*np.cos(phi) )
        gamma = np.atan2( O7jz, O7jx )
        theta = gamma - beta

        # Calculate the elbow point
        Oij = Rz_1i @ colvec([self.b + self.a*np.cos(theta), 0, self.a*np.sin(theta)])

        #print(f"Theta: {theta}\nPhi: {phi}\nElbow: {Oij}")

        return theta, phi, Oij
    
    def getArmPoints(self, armLetter='A'):
        if armLetter == 'A':
            return np.hstack([self.O01, self.O14, self.O74])
        elif armLetter == 'B':
            return np.hstack([self.O02, self.O25, self.O75])
        elif armLetter == 'C':
            return np.hstack([self.O03, self.O36, self.O76])
        else:
            print("Invalid arm letter")
            exit(0)

    def getBaseTriangle(self):
        return np.hstack([self.O01, self.O02, self.O03])

    def getPlatformTriangle(self):
        return np.hstack([self.O74, self.O75, self.O76])
        