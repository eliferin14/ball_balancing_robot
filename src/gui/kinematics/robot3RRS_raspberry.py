import numpy as np
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

from robot3RRS import robot3RRS

class robot3RRS_Raspberry(robot3RRS):

    def __init__(self, baseDistance, armLength, forearmLength, platDistance, pinA=16, pinB=20, pinC=21, alpha12=2/3*np.pi, alpha13=-2/3*np.pi, alpha45=2/3*np.pi, alpha46=-2/3*np.pi, maxTilt=0.2) -> None:
        
        # Create the "virtual robot"
        super().__init__(baseDistance, armLength, forearmLength, platDistance, alpha12, alpha13, alpha45, alpha46, maxTilt)

        # Define the motion flag
        self.enableMotion = True

        # Create the servo objects
        factory = PiGPIOFactory()        
        self.servoA = Servo(pinA, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
        self.servoB = Servo(pinB, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)
        self.servoC = Servo(pinC, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)

        # Move to zero position
        self.move(0, 0, 0)

    def enableMotion(self):
        self.enableMotion = True

    def disableMotion(self):
        self.enableMotion = False

        self.servoA.value = None;
        self.servoB.value = None;
        self.servoC.value = None;

    def isMotionEnabled(self):
        return self.enableMotion

    def move(self, thetaA=None, thetaB=None, thetaC=None):
        # Check if motion is enabled
        if not self.isMotionEnabled():
            return False
        
        # Check if arguments are passed
        # If they are, write these values, else use the self. values
        if thetaA is not None:
            self.servoA.value = thetaA
        else:
            self.servoA.value = self.theta1
        
        if thetaB is not None:
            self.servoB.value = thetaB
        else:
            self.servoB.value = self.theta2

        if thetaC is not None:
            self.servoC.value = thetaC
        else:
            self.servoC.value = self.theta3

if __name__ == "__main__":

    robot = robot3RRS_Raspberry(50, 50, 110, 75)
        
