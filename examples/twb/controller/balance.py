class BalanceController:
    """PID controller for two-wheeled balance robot."""

    def __init__(self):
        self.Kp = 50.0
        self.Ki = 10.0
        self.Kd = 15.0
        self.integral = 0.0
        self.prev_error = 0.0

    def control(self, theta, theta_dot, dt):
        error = -theta
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = error
        return self.Kp * error + self.Ki * self.integral + self.Kd * derivative
