# TWB Robot Balance Optimization

## Goal
Minimize the composite balance score for a two-wheeled balancing robot by tuning the controller in `controller/balance.py`.

## What you can change
- `controller/balance.py` — the entire file. You can change PID gains, add nonlinear terms, switch to LQR, add feedforward, etc.

## Constraints
- Must keep the `BalanceController` class with a `control(theta, theta_dot, dt) -> float` method
- No imports beyond Python stdlib and math
- Controller must stabilize the robot (theta must converge to 0)
- Keep the file under 100 lines

## Plant
- Inverted pendulum on wheels: theta'' = (g*sin(theta) - u*cos(theta)) / L
- L = 0.5 m, g = 9.81 m/s^2
- Initial: theta = 5 degrees, goal = 0 degrees

## Metric
Score = 0.7 * settling_time + 0.3 * max_overshoot_degrees. Lower is better.
- settling_time: time in seconds until |theta| < 0.5 degrees (and stays there)
- max_overshoot: peak |theta| in degrees during the entire run

## Strategy hints
- Higher Kp = faster response but more overshoot
- Higher Kd = more damping but slower response
- Ki helps with steady-state but can cause windup
- Consider anti-windup on the integral term
- Consider gain scheduling based on theta magnitude
- Consider adding a nonlinear term for large-angle correction
