import numpy as np


class SMCController:
    """Sliding Mode Controller with continuous approximation."""

    def __init__(self):
        self.K = 5.0
        self.lambda_ = 2.0
        self.epsilon = 0.1

    def compute_surface(self, error, error_dot):
        return error_dot + self.lambda_ * error

    def control(self, error, error_dot):
        s = self.compute_surface(error, error_dot)
        u_eq = self.lambda_ * error_dot
        u_sw = self.K * np.tanh(s / self.epsilon)
        return u_eq + u_sw
