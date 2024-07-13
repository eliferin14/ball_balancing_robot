import numpy as np
from scipy.optimize import fsolve

def find_points(P1, D1, P2, D2, d_desired):
    # Function to solve
    def equations(vars):
        t, s = vars
        r1 = P1 + t * D1
        r2 = P2 + s * D2
        dist = np.linalg.norm(r1 - r2)
        return [dist - d_desired]
    
    # Initial guess
    initial_guess = [0, 0]
    
    # Solve for t and s
    t, s = fsolve(equations, initial_guess)
    
    # Calculate points on the lines
    point_on_line1 = P1 + t * D1
    point_on_line2 = P2 + s * D2
    
    return point_on_line1, point_on_line2

# Example usage
P1 = np.array([1, 2, 3])
D1 = np.array([1, 0, 0])
P2 = np.array([4, 5, 6])
D2 = np.array([0, 1, 0])
d_desired = 5

point_on_line1, point_on_line2 = find_points(P1, D1, P2, D2, d_desired)
print("Point on Line 1:", point_on_line1)
print("Point on Line 2:", point_on_line2)