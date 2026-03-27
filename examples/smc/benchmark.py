import sys
import numpy as np

sys.path.insert(0, ".")
from controllers.surface import SMCController


def simulate_double_integrator():
    """x'' = u, track x_ref=1.0 step, 5s, dt=0.001."""
    dt = 0.001
    t_end = 5.0
    steps = int(t_end / dt)
    x_ref = 1.0

    x = 0.0
    x_dot = 0.0
    ctrl = SMCController()
    ise = 0.0

    for _ in range(steps):
        error = x_ref - x
        error_dot = -x_dot
        u = ctrl.control(error, error_dot)
        x_dot += u * dt
        x += x_dot * dt
        ise += error**2 * dt

    return ise


def simulate_inverted_pendulum():
    """theta'' = g*sin(theta)/L + u/(m*L^2), stabilize at 0 from theta0=0.3 rad, 5s, dt=0.001."""
    dt = 0.001
    t_end = 5.0
    steps = int(t_end / dt)
    g = 9.81
    L = 1.0
    m = 1.0

    theta = 0.3
    theta_dot = 0.0
    ctrl = SMCController()
    ise = 0.0

    for _ in range(steps):
        error = 0.0 - theta
        error_dot = -theta_dot
        u = ctrl.control(error, error_dot)
        theta_ddot = g * np.sin(theta) / L + u / (m * L**2)
        theta_dot += theta_ddot * dt
        theta += theta_dot * dt
        ise += theta**2 * dt

    return ise


def simulate_simple_pmsm():
    """di/dt = (-R*i + u)/L, track i_ref=1.0 step, 2s, dt=0.001."""
    dt = 0.001
    t_end = 2.0
    steps = int(t_end / dt)
    R = 1.0
    L_motor = 0.01
    i_ref = 1.0

    i = 0.0
    error_prev = i_ref
    ctrl = SMCController()
    ise = 0.0

    exp_term = np.exp(-(R / L_motor) * dt)

    for k in range(steps):
        error = i_ref - i
        error_dot = (error - error_prev) / dt if k > 0 else 0.0
        error_dot = np.clip(error_dot, -1000.0, 1000.0)
        u = ctrl.control(error, error_dot)
        u = np.clip(u, -50.0, 50.0)
        i = i * exp_term + (u / R) * (1.0 - exp_term)
        error_prev = error
        ise += (i_ref - i) ** 2 * dt

    return ise


def main():
    ise_di = simulate_double_integrator()
    ise_ip = simulate_inverted_pendulum()
    ise_pmsm = simulate_simple_pmsm()

    mean_ise = (ise_di + ise_ip + ise_pmsm) / 3.0
    print(mean_ise)


if __name__ == "__main__":
    main()
