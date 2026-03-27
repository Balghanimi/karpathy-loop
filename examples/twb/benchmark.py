"""TWB robot balance benchmark. Uses only Python stdlib (math)."""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from controller.balance import BalanceController


def simulate():
    g = 9.81
    L = 0.5
    T = 10.0
    dt = 0.001
    steps = int(T / dt)

    theta = math.radians(5.0)
    theta_dot = 0.0

    controller = BalanceController()

    thetas_deg = []

    for i in range(steps):
        t = i * dt
        theta_deg = math.degrees(theta)
        thetas_deg.append((t, abs(theta_deg)))

        u = controller.control(theta, theta_dot, dt)

        theta_ddot = (g * math.sin(theta) - u * math.cos(theta)) / L
        theta_dot += theta_ddot * dt
        theta += theta_dot * dt

    max_overshoot_degrees = max(val for _, val in thetas_deg)

    threshold = 0.5
    settle_duration = 0.5
    settling_time = T

    for i in range(len(thetas_deg)):
        t_i, val_i = thetas_deg[i]
        if val_i < threshold:
            settled = True
            for j in range(i, len(thetas_deg)):
                t_j, val_j = thetas_deg[j]
                if t_j - t_i > settle_duration:
                    break
                if val_j >= threshold:
                    settled = False
                    break
            if settled:
                settling_time = t_i
                break

    score = 0.7 * settling_time + 0.3 * max_overshoot_degrees
    print(score)


if __name__ == "__main__":
    simulate()
