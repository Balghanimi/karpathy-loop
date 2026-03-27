# Autoresearch: Autonomous Karpathy Loop Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, zero-dependency Python+git ratchet that autonomously improves any file via Claude Code's read-benchmark-generate loop.

**Architecture:** `iterate.py` is the single reusable core — it benchmarks, compares against best score, git-commits improvements or reverts regressions. `program.md` is the instruction file Claude Code reads to know what to optimize. `setup_project.py` scaffolds new projects. Two working examples (SMC controller, TWB robot) prove the tool works end-to-end.

**Tech Stack:** Python 3.8+ stdlib only (iterate.py, setup_project.py). numpy for examples only. git for version control/rollback.

---

## File Structure

```
D:/autoresearch/
├── iterate.py                  # The one reusable tool (copy to any project, edit 4 config lines)
├── setup_project.py            # Interactive scaffolder for new projects
├── examples/
│   ├── smc/                    # Working example: SMC controller optimization
│   │   ├── benchmark.py        # Simulates 3 plants, returns mean ISE
│   │   ├── program.md          # Claude Code instruction file
│   │   └── controllers/
│   │       └── surface.py      # The modifiable file
│   └── twb/                    # Working example: TWB robot balancing
│       ├── benchmark.py        # Simulates balance, returns composite score
│       ├── program.md          # Claude Code instruction file
│       └── controller/
│           └── balance.py      # The modifiable file
├── .gitignore
└── README.md
```

**Runtime state (created by iterate.py, gitignored):**
```
.autoresearch/
├── state.json                  # Best score, iteration count, metric config
└── log.jsonl                   # Full history of every run
```

---

### Task 1: Core iterate.py — Config, State, and Baseline

**Files:**
- Create: `D:/autoresearch/iterate.py`
- Create: `D:/autoresearch/.gitignore`

This task builds the foundation: CONFIG dict, state management, and baseline establishment on first run.

- [ ] **Step 1: Create .gitignore**

```
.autoresearch/
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 2: Write iterate.py with CONFIG, state management, and baseline logic**

```python
#!/usr/bin/env python3
"""iterate.py — Karpathy autoresearch ratchet.

Copy this file into any project directory and edit the CONFIG dict.
Runs benchmark, compares against best score, commits or reverts.
Zero dependencies beyond Python stdlib + git.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ─── USER CONFIG (edit these 4 lines per project) ───────────────────────────
CONFIG = {
    "benchmark_cmd": "python benchmark.py",
    "modifiable_files": ["controllers/surface.py"],
    "metric": "minimize",        # "minimize" or "maximize"
    "metric_name": "Mean ISE",
    "timeout": 300,              # benchmark timeout in seconds
    "max_iterations": 50,        # max autonomous iterations (0 = unlimited)
}
# ─────────────────────────────────────────────────────────────────────────────

STATE_DIR = Path(".autoresearch")
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "log.jsonl"


def ensure_git():
    """Initialize git repo if not already one."""
    if not Path(".git").exists():
        _run_git(["git", "init"])
        print("Initialized new git repository.")


def load_state():
    """Load state from disk, or return default state."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"best_score": None, "iteration": 0, "metric": CONFIG["metric"],
            "metric_name": CONFIG["metric_name"]}


def save_state(state):
    """Persist state to disk."""
    STATE_DIR.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def append_log(entry):
    """Append a log entry to the JSONL log file."""
    STATE_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def run_benchmark():
    """Run the benchmark command and parse the last line as a float.

    Returns (score, stdout) on success, raises on failure.
    """
    try:
        result = subprocess.run(
            CONFIG["benchmark_cmd"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=CONFIG["timeout"],
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Benchmark timed out after {CONFIG['timeout']}s")

    if result.returncode != 0:
        stderr_snippet = result.stderr.strip()[-500:] if result.stderr else "(no stderr)"
        raise RuntimeError(
            f"Benchmark exited with code {result.returncode}\n{stderr_snippet}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("Benchmark produced no output")

    last_line = stdout.strip().split("\n")[-1].strip()
    try:
        score = float(last_line)
    except ValueError:
        raise RuntimeError(f"Could not parse last line as float: '{last_line}'")

    return score, stdout


def is_improved(old_score, new_score):
    """Check if new_score is an improvement over old_score."""
    if old_score is None:
        return True
    if CONFIG["metric"] == "minimize":
        return new_score < old_score
    return new_score > old_score


def _run_git(cmd):
    """Run a git command and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def git_commit(state, old_score, new_score):
    """Stage modifiable files and commit with iteration message."""
    for f in CONFIG["modifiable_files"]:
        _run_git(["git", "add", f])
    msg = (f"iter-{state['iteration']}: {CONFIG['metric_name']} "
           f"{old_score:.6f} -> {new_score:.6f}")
    _run_git(["git", "commit", "-m", msg])
    return msg


def git_revert():
    """Revert modifiable files to last committed version."""
    for f in CONFIG["modifiable_files"]:
        _run_git(["git", "checkout", "HEAD", "--", f])


def get_recent_git_log(n=5):
    """Get recent git log as a formatted string."""
    try:
        result = subprocess.run(
            ["git", "log", f"--oneline", f"-{n}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return "(no git history)"


def format_paste_block(score, state, improved, old_score=None):
    """Format the paste-ready output block for Claude Code."""
    direction = CONFIG["metric"]
    metric = CONFIG["metric_name"]
    iteration = state["iteration"]
    files = " ".join(CONFIG["modifiable_files"])

    lines = [f"Score: {score:.6f} ({metric}, {direction})."]

    if improved and old_score is not None:
        lines.append(f"IMPROVED iter-{iteration}: {old_score:.6f} -> {score:.6f}")
    elif not improved and old_score is not None:
        lines.append(f"REVERTED iter-{iteration}: {score:.6f} was worse than best {old_score:.6f}")
    else:
        lines.append(f"BASELINE iter-{iteration}: {score:.6f} (first run)")

    lines.append(f"Git log (recent):")
    for log_line in get_recent_git_log().split("\n"):
        if log_line.strip():
            lines.append(f"  {log_line}")

    lines.append(f"Improve {files} further. Give me the complete file.")

    return "\n".join(lines)


def cmd_run():
    """Main run: benchmark, compare, commit or revert."""
    ensure_git()
    state = load_state()
    old_score = state["best_score"]

    print(f"[iter-{state['iteration'] + 1}] Running benchmark: {CONFIG['benchmark_cmd']}")

    try:
        score, stdout = run_benchmark()
    except RuntimeError as e:
        print(f"BENCHMARK FAILED: {e}")
        git_revert()
        print("Reverted modifiable files.")
        append_log({
            "iteration": state["iteration"] + 1,
            "timestamp": time.time(),
            "status": "failed",
            "error": str(e),
        })
        state["iteration"] += 1
        save_state(state)
        return False

    improved = is_improved(old_score, score)
    state["iteration"] += 1

    log_entry = {
        "iteration": state["iteration"],
        "timestamp": time.time(),
        "score": score,
        "best_score": old_score,
        "status": "improved" if improved else ("baseline" if old_score is None else "reverted"),
    }

    if improved:
        if old_score is not None:
            commit_msg = git_commit(state, old_score, score)
            log_entry["commit_msg"] = commit_msg
        else:
            # Baseline: commit initial state
            for f in CONFIG["modifiable_files"]:
                _run_git(["git", "add", f])
            # Also add benchmark.py and program.md if they exist
            for extra in ["benchmark.py", "program.md"]:
                if Path(extra).exists():
                    _run_git(["git", "add", extra])
            _run_git(["git", "commit", "-m",
                       f"iter-{state['iteration']}: baseline {CONFIG['metric_name']} {score:.6f}"])
        state["best_score"] = score
    else:
        git_revert()

    save_state(state)
    append_log(log_entry)

    output = format_paste_block(
        score if improved else old_score,
        state, improved, old_score
    )
    print("\n" + output)
    return improved


def cmd_status():
    """Show current status."""
    state = load_state()
    if state["best_score"] is None:
        print("No runs yet. Run `python iterate.py` to establish baseline.")
        return

    # Count stats from log
    total = 0
    improved_count = 0
    failed_count = 0
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            for line in f:
                entry = json.loads(line)
                total += 1
                if entry.get("status") == "improved":
                    improved_count += 1
                elif entry.get("status") == "failed":
                    failed_count += 1

    hit_rate = (improved_count / total * 100) if total > 0 else 0

    print(f"Best {CONFIG['metric_name']}: {state['best_score']:.6f} ({CONFIG['metric']})")
    print(f"Iterations: {state['iteration']}")
    print(f"Improvements: {improved_count}/{total} ({hit_rate:.0f}% hit rate)")
    if failed_count:
        print(f"Failures: {failed_count}")
    print(f"\nRecent git log:")
    print(get_recent_git_log(10))


def cmd_reset():
    """Reset state files (clear history)."""
    if STATE_DIR.exists():
        import shutil
        shutil.rmtree(STATE_DIR)
    print("State cleared. Next run will establish a new baseline.")


def cmd_history():
    """Show full improvement history."""
    if not LOG_FILE.exists():
        print("No history yet.")
        return

    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            iteration = entry.get("iteration", "?")
            status = entry.get("status", "unknown")
            score = entry.get("score")
            best = entry.get("best_score")

            if status == "baseline":
                print(f"  iter-{iteration}: BASELINE {score:.6f}")
            elif status == "improved":
                print(f"  iter-{iteration}: IMPROVED {best:.6f} -> {score:.6f}")
            elif status == "reverted":
                print(f"  iter-{iteration}: reverted ({score:.6f} worse than {best:.6f})")
            elif status == "failed":
                print(f"  iter-{iteration}: FAILED ({entry.get('error', 'unknown error')})")


def main():
    """Entry point with subcommand dispatch."""
    args = sys.argv[1:]

    if not args:
        try:
            cmd_run()
        except KeyboardInterrupt:
            print("\nInterrupted. Reverting uncommitted changes...")
            try:
                git_revert()
            except Exception:
                pass
            print("Reverted. Exiting.")
            sys.exit(1)
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "reset":
        cmd_reset()
    elif args[0] == "history":
        cmd_history()
    else:
        print(f"Unknown command: {args[0]}")
        print("Usage: python iterate.py [status|reset|history]")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit initial iterate.py**

```bash
cd D:/autoresearch
git add iterate.py .gitignore
git commit -m "feat: iterate.py core ratchet with config, state, benchmark, git commit/revert"
```

---

### Task 2: SMC Example — benchmark.py and controllers/surface.py

**Files:**
- Create: `D:/autoresearch/examples/smc/controllers/surface.py`
- Create: `D:/autoresearch/examples/smc/benchmark.py`
- Create: `D:/autoresearch/examples/smc/program.md`

- [ ] **Step 1: Create controllers/surface.py**

```python
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
        u_eq = -self.lambda_ * error_dot
        u_sw = -self.K * np.tanh(s / self.epsilon)
        return u_eq + u_sw
```

- [ ] **Step 2: Create benchmark.py**

```python
"""SMC Benchmark — 3 plants, returns mean ISE.

Plants:
  1. DoubleIntegrator: x'' = u, track x_ref=1.0, 5s, dt=0.001
  2. InvertedPendulum: theta'' = g*sin(theta)/L + u/(m*L^2), stabilize at 0, 5s, dt=0.001
  3. SimplePMSM: di/dt = (-R*i + u)/L, track i_ref=1.0, 2s, dt=0.001
"""

import numpy as np
import sys
import os

# Add parent so we can import from controllers/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from controllers.surface import SMCController


def simulate_double_integrator(ctrl, dt=0.001, T=5.0, x_ref=1.0):
    """x'' = u, track step reference."""
    steps = int(T / dt)
    x, x_dot = 0.0, 0.0
    ise = 0.0
    for _ in range(steps):
        error = x_ref - x
        error_dot = -x_dot
        u = ctrl.control(error, error_dot)
        x_dot += u * dt
        x += x_dot * dt
        ise += error ** 2 * dt
    return ise


def simulate_inverted_pendulum(ctrl, dt=0.001, T=5.0):
    """theta'' = g*sin(theta)/L + u/(m*L^2), stabilize at theta=0 from theta0=0.3 rad."""
    g, L, m = 9.81, 1.0, 1.0
    steps = int(T / dt)
    theta, theta_dot = 0.3, 0.0
    ise = 0.0
    for _ in range(steps):
        error = 0.0 - theta
        error_dot = -theta_dot
        u = ctrl.control(error, error_dot)
        theta_ddot = g * np.sin(theta) / L + u / (m * L ** 2)
        theta_dot += theta_ddot * dt
        theta += theta_dot * dt
        ise += error ** 2 * dt
    return ise


def simulate_pmsm(ctrl, dt=0.001, T=2.0, i_ref=1.0):
    """di/dt = (-R*i + u) / L, track step reference."""
    R, L_motor = 1.0, 0.01
    steps = int(T / dt)
    i = 0.0
    ise = 0.0
    for _ in range(steps):
        error = i_ref - i
        error_dot = -((-R * i) / L_motor)  # approximate derivative
        u = ctrl.control(error, error_dot)
        di_dt = (-R * i + u) / L_motor
        i += di_dt * dt
        ise += error ** 2 * dt
    return ise


def main():
    ctrl = SMCController()
    ise_di = simulate_double_integrator(ctrl)
    ctrl_ip = SMCController()
    ise_ip = simulate_inverted_pendulum(ctrl_ip)
    ctrl_pm = SMCController()
    ise_pm = simulate_pmsm(ctrl_pm)
    mean_ise = (ise_di + ise_ip + ise_pm) / 3.0
    print(f"{mean_ise:.6f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create program.md**

```markdown
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
```

- [ ] **Step 4: Test the SMC example runs**

```bash
cd D:/autoresearch/examples/smc
python benchmark.py
```

Expected: a single float printed (the mean ISE score).

- [ ] **Step 5: Test iterate.py baseline in SMC example**

```bash
cd D:/autoresearch/examples/smc
cp ../../iterate.py .
# Edit CONFIG in the local copy to match SMC example (already correct defaults)
python iterate.py
```

Expected: "BASELINE iter-1: <score>" output with git commit.

- [ ] **Step 6: Commit SMC example**

```bash
cd D:/autoresearch
git add examples/smc/
git commit -m "feat: SMC example with 3-plant benchmark and program.md"
```

---

### Task 3: TWB Example — benchmark.py and controller/balance.py

**Files:**
- Create: `D:/autoresearch/examples/twb/controller/balance.py`
- Create: `D:/autoresearch/examples/twb/benchmark.py`
- Create: `D:/autoresearch/examples/twb/program.md`

- [ ] **Step 1: Create controller/balance.py**

```python
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
```

- [ ] **Step 2: Create benchmark.py**

```python
"""TWB Benchmark — inverted pendulum on wheels, returns composite score.

Simulates a two-wheeled balancing robot.
theta'' = (g*sin(theta) - u*cos(theta)) / L
Start: theta=5 degrees, goal=0.
Score = 0.7 * settling_time + 0.3 * max_overshoot_degrees (minimize).
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from controller.balance import BalanceController


def simulate(dt=0.001, T=10.0):
    g = 9.81
    L = 0.5
    theta = math.radians(5.0)
    theta_dot = 0.0

    ctrl = BalanceController()

    max_overshoot_deg = 0.0
    settling_time = T  # default: never settled
    settled = False
    threshold_rad = math.radians(0.5)

    for step in range(int(T / dt)):
        t = step * dt
        u = ctrl.control(theta, theta_dot, dt)

        theta_ddot = (g * math.sin(theta) - u * math.cos(theta)) / L
        theta_dot += theta_ddot * dt
        theta += theta_dot * dt

        overshoot_deg = abs(math.degrees(theta))
        if overshoot_deg > max_overshoot_deg:
            max_overshoot_deg = overshoot_deg

        # Check settling: once |theta| < 0.5 deg and stays there
        if not settled and abs(theta) < threshold_rad:
            # Check it stays settled for 0.5s
            settled = True
            settling_time = t

        if settled and abs(theta) >= threshold_rad:
            settled = False
            settling_time = T

    score = 0.7 * settling_time + 0.3 * max_overshoot_deg
    return score


def main():
    score = simulate()
    print(f"{score:.6f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create program.md**

```markdown
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
- settling_time: time in seconds until |theta| < 0.5 degrees
- max_overshoot: peak |theta| in degrees during the entire run

## Strategy hints
- Higher Kp = faster response but more overshoot
- Higher Kd = more damping but slower response
- Ki helps with steady-state but can cause windup
- Consider anti-windup on the integral term
- Consider gain scheduling based on theta magnitude
- Consider adding a nonlinear term for large-angle correction
```

- [ ] **Step 4: Test the TWB example runs**

```bash
cd D:/autoresearch/examples/twb
python benchmark.py
```

Expected: a single float printed (the composite score).

- [ ] **Step 5: Commit TWB example**

```bash
cd D:/autoresearch
git add examples/twb/
git commit -m "feat: TWB robot example with balance benchmark and program.md"
```

---

### Task 4: setup_project.py — Interactive Scaffolder

**Files:**
- Create: `D:/autoresearch/setup_project.py`

- [ ] **Step 1: Write setup_project.py**

```python
#!/usr/bin/env python3
"""Interactive scaffolder for new autoresearch projects.

Creates a project directory with iterate.py configured for your project,
a benchmark.py template, program.md template, and .gitignore.
"""

import os
import sys
from pathlib import Path


ITERATE_TEMPLATE = '''#!/usr/bin/env python3
"""iterate.py — Karpathy autoresearch ratchet.

Copy this file into any project directory and edit the CONFIG dict.
Runs benchmark, compares against best score, commits or reverts.
Zero dependencies beyond Python stdlib + git.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# --- USER CONFIG (edit these 4 lines per project) ---
CONFIG = {{
    "benchmark_cmd": "{benchmark_cmd}",
    "modifiable_files": {modifiable_files},
    "metric": "{metric}",
    "metric_name": "{metric_name}",
    "timeout": 300,
    "max_iterations": 50,
}}
# -----------------------------------------------------

STATE_DIR = Path(".autoresearch")
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "log.jsonl"


def ensure_git():
    if not Path(".git").exists():
        _run_git(["git", "init"])
        print("Initialized new git repository.")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {{"best_score": None, "iteration": 0, "metric": CONFIG["metric"],
            "metric_name": CONFIG["metric_name"]}}


def save_state(state):
    STATE_DIR.mkdir(exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def append_log(entry):
    STATE_DIR.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\\n")


def run_benchmark():
    try:
        result = subprocess.run(
            CONFIG["benchmark_cmd"], shell=True,
            capture_output=True, text=True, timeout=CONFIG["timeout"],
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Benchmark timed out after {{CONFIG['timeout']}}s")
    if result.returncode != 0:
        stderr_snippet = result.stderr.strip()[-500:] if result.stderr else "(no stderr)"
        raise RuntimeError(f"Benchmark exited with code {{result.returncode}}\\n{{stderr_snippet}}")
    stdout = result.stdout.strip()
    if not stdout:
        raise RuntimeError("Benchmark produced no output")
    last_line = stdout.strip().split("\\n")[-1].strip()
    try:
        score = float(last_line)
    except ValueError:
        raise RuntimeError(f"Could not parse last line as float: '{{last_line}}'")
    return score, stdout


def is_improved(old_score, new_score):
    if old_score is None:
        return True
    if CONFIG["metric"] == "minimize":
        return new_score < old_score
    return new_score > old_score


def _run_git(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {{' '.join(cmd)}}\\n{{result.stderr}}")
    return result.stdout.strip()


def git_commit(state, old_score, new_score):
    for f in CONFIG["modifiable_files"]:
        _run_git(["git", "add", f])
    msg = (f"iter-{{state['iteration']}}: {{CONFIG['metric_name']}} "
           f"{{old_score:.6f}} -> {{new_score:.6f}}")
    _run_git(["git", "commit", "-m", msg])
    return msg


def git_revert():
    for f in CONFIG["modifiable_files"]:
        _run_git(["git", "checkout", "HEAD", "--", f])


def get_recent_git_log(n=5):
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{{n}}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return "(no git history)"


def format_paste_block(score, state, improved, old_score=None):
    direction = CONFIG["metric"]
    metric = CONFIG["metric_name"]
    iteration = state["iteration"]
    files = " ".join(CONFIG["modifiable_files"])
    lines = [f"Score: {{score:.6f}} ({{metric}}, {{direction}})."]
    if improved and old_score is not None:
        lines.append(f"IMPROVED iter-{{iteration}}: {{old_score:.6f}} -> {{score:.6f}}")
    elif not improved and old_score is not None:
        lines.append(f"REVERTED iter-{{iteration}}: {{score:.6f}} was worse than best {{old_score:.6f}}")
    else:
        lines.append(f"BASELINE iter-{{iteration}}: {{score:.6f}} (first run)")
    lines.append("Git log (recent):")
    for log_line in get_recent_git_log().split("\\n"):
        if log_line.strip():
            lines.append(f"  {{log_line}}")
    lines.append(f"Improve {{files}} further. Give me the complete file.")
    return "\\n".join(lines)


def cmd_run():
    ensure_git()
    state = load_state()
    old_score = state["best_score"]
    print(f"[iter-{{state['iteration'] + 1}}] Running benchmark: {{CONFIG['benchmark_cmd']}}")
    try:
        score, stdout = run_benchmark()
    except RuntimeError as e:
        print(f"BENCHMARK FAILED: {{e}}")
        git_revert()
        print("Reverted modifiable files.")
        append_log({{
            "iteration": state["iteration"] + 1, "timestamp": time.time(),
            "status": "failed", "error": str(e),
        }})
        state["iteration"] += 1
        save_state(state)
        return False
    improved = is_improved(old_score, score)
    state["iteration"] += 1
    log_entry = {{
        "iteration": state["iteration"], "timestamp": time.time(),
        "score": score, "best_score": old_score,
        "status": "improved" if improved else ("baseline" if old_score is None else "reverted"),
    }}
    if improved:
        if old_score is not None:
            commit_msg = git_commit(state, old_score, score)
            log_entry["commit_msg"] = commit_msg
        else:
            for f in CONFIG["modifiable_files"]:
                _run_git(["git", "add", f])
            for extra in ["benchmark.py", "program.md"]:
                if Path(extra).exists():
                    _run_git(["git", "add", extra])
            _run_git(["git", "commit", "-m",
                       f"iter-{{state['iteration']}}: baseline {{CONFIG['metric_name']}} {{score:.6f}}"])
        state["best_score"] = score
    else:
        git_revert()
    save_state(state)
    append_log(log_entry)
    output = format_paste_block(
        score if improved else old_score, state, improved, old_score
    )
    print("\\n" + output)
    return improved


def cmd_status():
    state = load_state()
    if state["best_score"] is None:
        print("No runs yet. Run `python iterate.py` to establish baseline.")
        return
    total, improved_count, failed_count = 0, 0, 0
    if LOG_FILE.exists():
        with open(LOG_FILE) as f:
            for line in f:
                entry = json.loads(line)
                total += 1
                if entry.get("status") == "improved":
                    improved_count += 1
                elif entry.get("status") == "failed":
                    failed_count += 1
    hit_rate = (improved_count / total * 100) if total > 0 else 0
    print(f"Best {{CONFIG['metric_name']}}: {{state['best_score']:.6f}} ({{CONFIG['metric']}})")
    print(f"Iterations: {{state['iteration']}}")
    print(f"Improvements: {{improved_count}}/{{total}} ({{hit_rate:.0f}}% hit rate)")
    if failed_count:
        print(f"Failures: {{failed_count}}")
    print(f"\\nRecent git log:")
    print(get_recent_git_log(10))


def cmd_reset():
    if STATE_DIR.exists():
        import shutil
        shutil.rmtree(STATE_DIR)
    print("State cleared. Next run will establish a new baseline.")


def cmd_history():
    if not LOG_FILE.exists():
        print("No history yet.")
        return
    with open(LOG_FILE) as f:
        for line in f:
            entry = json.loads(line)
            iteration = entry.get("iteration", "?")
            status = entry.get("status", "unknown")
            score = entry.get("score")
            best = entry.get("best_score")
            if status == "baseline":
                print(f"  iter-{{iteration}}: BASELINE {{score:.6f}}")
            elif status == "improved":
                print(f"  iter-{{iteration}}: IMPROVED {{best:.6f}} -> {{score:.6f}}")
            elif status == "reverted":
                print(f"  iter-{{iteration}}: reverted ({{score:.6f}} worse than {{best:.6f}})")
            elif status == "failed":
                print(f"  iter-{{iteration}}: FAILED ({{entry.get('error', 'unknown error')}})")


def main():
    args = sys.argv[1:]
    if not args:
        try:
            cmd_run()
        except KeyboardInterrupt:
            print("\\nInterrupted. Reverting uncommitted changes...")
            try:
                git_revert()
            except Exception:
                pass
            print("Reverted. Exiting.")
            sys.exit(1)
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "reset":
        cmd_reset()
    elif args[0] == "history":
        cmd_history()
    else:
        print(f"Unknown command: {{args[0]}}")
        print("Usage: python iterate.py [status|reset|history]")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

BENCHMARK_TEMPLATE = '''"""Benchmark for {project_name}.

Implement your evaluation logic here.
The ONLY requirement: print a single float as the last line of stdout.
"""


def evaluate():
    # TODO: implement your benchmark
    # Return a single number (the score to optimize)
    score = 0.0
    return score


if __name__ == "__main__":
    score = evaluate()
    print(f"{{score:.6f}}")
'''

PROGRAM_TEMPLATE = '''# {project_name}

## Goal
Describe what you want to optimize and why.

## What you can change
- List the modifiable files and what kinds of changes are allowed.

## Constraints
- Must keep the same class/function interface
- List any import restrictions
- File size limits

## Metric
{metric_name} ({metric}). Describe what it measures.

## Strategy hints
- Hint 1
- Hint 2
'''

GITIGNORE_TEMPLATE = """.autoresearch/
__pycache__/
*.pyc
.DS_Store
"""


def main():
    print("=== Autoresearch Project Scaffolder ===\n")

    project_name = input("Project name: ").strip()
    if not project_name:
        print("Error: project name required.")
        sys.exit(1)

    metric_name = input("Metric name [Score]: ").strip() or "Score"
    metric = input("Direction (minimize/maximize) [minimize]: ").strip() or "minimize"
    if metric not in ("minimize", "maximize"):
        print("Error: direction must be 'minimize' or 'maximize'.")
        sys.exit(1)

    benchmark_cmd = input("Benchmark command [python benchmark.py]: ").strip() or "python benchmark.py"
    mod_files_raw = input("Modifiable file(s) (comma-separated): ").strip()
    if not mod_files_raw:
        print("Error: at least one modifiable file required.")
        sys.exit(1)

    modifiable_files = [f.strip() for f in mod_files_raw.split(",")]
    mod_files_repr = repr(modifiable_files)

    project_dir = Path(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create iterate.py with configured values
    iterate_content = ITERATE_TEMPLATE.format(
        benchmark_cmd=benchmark_cmd,
        modifiable_files=mod_files_repr,
        metric=metric,
        metric_name=metric_name,
    )
    (project_dir / "iterate.py").write_text(iterate_content, encoding="utf-8")

    # Create benchmark.py template
    bench_content = BENCHMARK_TEMPLATE.format(project_name=project_name)
    (project_dir / "benchmark.py").write_text(bench_content, encoding="utf-8")

    # Create program.md template
    program_content = PROGRAM_TEMPLATE.format(
        project_name=project_name,
        metric_name=metric_name,
        metric=metric,
    )
    (project_dir / "program.md").write_text(program_content, encoding="utf-8")

    # Create .gitignore
    (project_dir / ".gitignore").write_text(GITIGNORE_TEMPLATE, encoding="utf-8")

    # Create directories for modifiable files
    for f in modifiable_files:
        file_path = project_dir / f
        file_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nCreated {project_name}/")
    print(f"  ├── iterate.py          (configured with your settings)")
    print(f"  ├── benchmark.py        (template — implement evaluate())")
    print(f"  ├── program.md          (describe your project goals here)")
    print(f"  └── .gitignore")
    print(f"\nNext steps:")
    print(f"  1. cd {project_name}")
    print(f"  2. Implement benchmark.py (must print a single float as last line)")
    for f in modifiable_files:
        print(f"  3. Create your modifiable file: {f}")
    print(f"  4. Run: python iterate.py          (establishes baseline)")
    print(f"  5. Let Claude Code read program.md and run the autonomous loop")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit setup_project.py**

```bash
cd D:/autoresearch
git add setup_project.py
git commit -m "feat: interactive project scaffolder"
```

---

### Task 5: README.md

**Files:**
- Create: `D:/autoresearch/README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Autoresearch

A zero-dependency Python+git ratchet for autonomous iterative code improvement. Claude Code reads a `program.md` instruction file, generates improved code, and `iterate.py` handles benchmarking, scoring, and git commit/revert. No API keys. No pip installs. Pure Python stdlib + git.

## Requirements

- Python 3.8+
- git
- numpy (for examples only — iterate.py itself needs nothing)
- Claude Code with Max plan (for autonomous loop)

## Quick Start (SMC Example)

```bash
cd examples/smc
python benchmark.py          # verify it runs, prints a float
python iterate.py             # establishes baseline, first git commit
python iterate.py status      # show current best score
```

## How It Works

```
Claude Code reads program.md (what to optimize)
        |
        v
Reads modifiable file + git log
        |
        v
Generates improved version --> Writes to file
        |
        v
Runs: python iterate.py
        |
        v
  +-----------+
  | Benchmark |---> Score improved? --YES--> git commit, update best
  +-----------+                    --NO---> git revert
        |
        v
Claude Code reads output, loops back
```

## Use On Your Own Project

### Option A: Copy iterate.py (fastest)

1. Copy `iterate.py` into your project directory
2. Edit the 4 CONFIG lines at the top:
   ```python
   CONFIG = {
       "benchmark_cmd": "python benchmark.py",
       "modifiable_files": ["src/my_algorithm.py"],
       "metric": "minimize",        # or "maximize"
       "metric_name": "Mean ISE",
   }
   ```
3. Write a `benchmark.py` that prints a single float as its last line
4. Create a `program.md` describing what to optimize (Claude Code reads this)
5. Run: `python iterate.py`

### Option B: Use the scaffolder

```bash
python setup_project.py
```

Walks you through creating a new project with iterate.py pre-configured.

## Commands

| Command | What it does |
|---------|-------------|
| `python iterate.py` | Run benchmark, commit or revert |
| `python iterate.py status` | Show best score, hit rate, recent log |
| `python iterate.py reset` | Clear state, start fresh |
| `python iterate.py history` | Show full improvement history |

## Writing a Good benchmark.py

- **Deterministic**: same code = same score (use fixed seeds if randomness is involved)
- **Fast**: under 60 seconds ideally, 300s max (configurable via CONFIG["timeout"])
- **Single float output**: the last line of stdout must be parseable as a float
- **Non-zero exit on failure**: return non-zero exit code if something crashes

## Writing a Good program.md

This is the instruction file Claude Code reads to understand your project:

- **Goal**: what metric to optimize and why
- **What you can change**: which files and what kinds of modifications
- **Constraints**: interface requirements, import restrictions, file size limits
- **Metric explanation**: what the score measures physically
- **Strategy hints**: domain knowledge that helps guide the search

## File Structure

```
your-project/
├── iterate.py          # The ratchet (edit 4 CONFIG lines)
├── benchmark.py        # Your evaluation (prints a float)
├── program.md          # Instructions for Claude Code
├── your_code.py        # The file being optimized
└── .autoresearch/      # Created automatically
    ├── state.json      # Best score, iteration count
    └── log.jsonl       # Full run history
```

## License

MIT
```

- [ ] **Step 2: Commit README**

```bash
cd D:/autoresearch
git add README.md
git commit -m "docs: README with quick start and usage guide"
```

---

### Task 6: End-to-End Verification

- [ ] **Step 1: Verify SMC example benchmark runs**

```bash
cd D:/autoresearch/examples/smc
python benchmark.py
```

Expected: a float like `0.XXXXXX`

- [ ] **Step 2: Verify TWB example benchmark runs**

```bash
cd D:/autoresearch/examples/twb
python benchmark.py
```

Expected: a float like `X.XXXXXX`

- [ ] **Step 3: Verify iterate.py baseline works in SMC example**

```bash
cd D:/autoresearch/examples/smc
python ../../iterate.py
```

Expected: baseline output with git commit message.

- [ ] **Step 4: Verify iterate.py status works**

```bash
cd D:/autoresearch/examples/smc
python ../../iterate.py status
```

Expected: shows best score and iteration count.

- [ ] **Step 5: Verify iterate.py reset works**

```bash
cd D:/autoresearch/examples/smc
python ../../iterate.py reset
```

Expected: "State cleared."

- [ ] **Step 6: Final commit — tag v0.1.0**

```bash
cd D:/autoresearch
git add -A
git commit -m "chore: autoresearch v0.1.0 — autonomous Karpathy ratchet scaffold"
git tag v0.1.0
```
