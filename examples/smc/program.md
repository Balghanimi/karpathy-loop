# SMC Controller Optimization

## Goal
Minimize the mean Integrated Squared Error (ISE) across 3 plants by tuning the SMC controller in `controllers/surface.py`.

## What you can change
- `controllers/surface.py` — the entire file. You can change gains (K, lambda_, epsilon), add adaptive logic, change the surface function, add integral terms, etc.

## Constraints
- Must keep the `SMCController` class with a `control(error, error_dot) -> float` method
- Must use only numpy (no other imports)
- Controller must be stable (no divergence) on all 3 plants
- Keep the file under 100 lines

## Plants being tested
1. **DoubleIntegrator**: x'' = u, track x_ref=1.0 step, 5s
2. **InvertedPendulum**: theta'' = g*sin(theta)/L + u/(m*L^2), stabilize from 0.3 rad, 5s
3. **SimplePMSM**: di/dt = (-R*i + u)/L, track i_ref=1.0 step, 2s

## Metric
Mean ISE across all 3 plants. Lower is better.

## Strategy hints
- Higher K = faster convergence but more chattering
- Higher lambda_ = faster sliding but can overshoot
- Smaller epsilon = sharper switching but more chattering
- Consider integral sliding mode to reduce steady-state error
- Consider adaptive gains that depend on the error magnitude
- Consider nonlinear surface functions (terminal, non-singular terminal)
