import control as ct
import numpy as np
import matplotlib.pyplot as plt
import time

# Class to design a PID controller using the phase margin technique

# The idea is to create a class that manages everything: from the definition of the gains to the control signal calculation
# Ideally it also manages the continuos and discrete time cases

class PID():

    def __init__(self, plantTF, risingTime=None, settlingTime=None, overshoot=None, samplingTime=0, referenceOrder=1):

        s = ct.TransferFunction.s

        self.Ts = samplingTime
        self.integral = 0

        # Save the plant function
        self.plant = plantTF

        # Count poles at the origin 
        plantPoles = ct.poles(self.plant)
        l = np.sum(np.isclose(plantPoles, 0))
        print(f"Plant poles at origin: {l}")

        # Add poles if needed (the reference signal has more poles that the plant)
        if referenceOrder > l: pass

        # Time domain specs -> frequency domani specs
        # Using Zampieri's approximations
        wc = 2 / risingTime
        phim = 1.04 - 0.8*overshoot
        #delta = np.log(1/overshoot) / ( np.sqrt(np.pi**2 + np.log(1/overshoot)**2) )
        print(f"Cutoff frequency: {wc}; Phase margin: {phim}")

        # Evaluate plant at the cutoff frequency
        P_jwc = ct.evalfr(self.plant, 1j*wc)

        # Define PID gain and phase at the cutoff frequency
        C_jwc_gain = 1 / abs(P_jwc)
        C_jwc_phase = phim - np.pi - np.angle(P_jwc)
        if C_jwc_phase < np.pi: C_jwc_phase += 2*np.pi
        print(f"Controller at wc: gain={C_jwc_gain}, phase={C_jwc_phase}")

        # Define phase margin of controller+AA+ZOH
        phiAA = 0
        phiZOH = wc*samplingTime/2
        phi = C_jwc_phase + phiAA + phiZOH

        # Choose architechture and define gains
        print(f"Phase margin: {phi}")
        if phi > 0 and phi < np.pi/2:   # PD
            self.Kp = 1 / abs(P_jwc) * np.cos(phi)
            Td = np.tan(phi) / wc
            self.Ki = 0
            self.Kd = Td
        else:
            print("Phase margin is outside of controllable region")
            exit(0)
        
        print(f"Kp: {self.Kp}, Ki: {self.Ki}, Kd: {self.Kd}")





        # Build the controller
        self.controller = ct.TransferFunction( [self.Kd, self.Kp, self.Ki], [1, 0] )
        if self.Kd > 0: self.controller *= 1 / (s + 10*wc)
        print(self.controller)

        # Closed loop system
        self.closedLoopTF = ct.feedback( self.controller*self.plant, 1)

        # Convert to digital
        if self.Ts > 0:
            self.controllerDiscrete = ct.sample_system(self.controller, self.Ts, method='bilinear')
            print(self.controllerDiscrete)

    def getControlSignal(self, newMeasurement, target):

        t = time.time()
        deltaTime = t - self.oldTime

        error = newMeasurement - target

        # Compute integral
        self.integral += error * deltaTime

        # Compute derivative
        derivative = (error - self.oldError) / deltaTime

        # Sum all contributions
        self.u = error*self.Kp + self.integral*self.Ki + derivative*self.Kd

        # Save the value for next cycle
        self.oldError = error
        self.oldTime = t

        return self.u

    def stepResponse(self, system):
        t, y = ct.step_response(system)
        plt.figure(figsize=(8, 5))
        plt.plot(t, y)
        plt.title('Closed-Loop Step Response with PID Controller')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Response')
        plt.grid()
        plt.show()


if __name__ == "__main__":
    s = ct.TransferFunction.s

    # Constants
    Ts = 0.1
    g = 9.81
    
    lowpass = 1/(s+5)       
    plantTF = 3.0/5*g/s**2 * lowpass

    rising = 2
    overshoot = 0.05

    pid = PID(plantTF, risingTime=rising, overshoot=overshoot, samplingTime=0.1)

    pid.stepResponse(pid.controllerDiscrete)