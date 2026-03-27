"""
iterate.py -- single reusable ratchet tool for autoresearch.

Copy this file into any project. Configure the CONFIG dict below.
Run: python iterate.py
Zero dependencies beyond Python stdlib + git.
"""

import json
import os
import signal
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# CONFIG -- edit these for your project
# ---------------------------------------------------------------------------
CONFIG = {
    "benchmark_cmd": "python benchmark.py",
    "modifiable_files": ["controllers/surface.py"],
    "metric": "minimize",          # "minimize" or "maximize"
    "metric_name": "Mean ISE",
    "timeout": 300,                # seconds
    "max_iterations": 50,          # 0 = unlimited
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_DIR = ".autoresearch"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
LOG_FILE = os.path.join(STATE_DIR, "log.jsonl")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


def _load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"best_score": None, "iteration": 0}


def _save_state(state):
    _ensure_state_dir()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _append_log(entry):
    _ensure_state_dir()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _read_log():
    if not os.path.isfile(LOG_FILE):
        return []
    entries = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _is_better(new_score, old_score):
    if old_score is None:
        return True
    if CONFIG["metric"] == "minimize":
        return new_score < old_score
    return new_score > old_score


def _git(*args):
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True,
        text=True,
    )
    return result


def _git_check(msg, *args):
    result = _git(*args)
    if result.returncode != 0:
        print("git {} failed: {}".format(msg, result.stderr.strip()))
    return result


def _ensure_git_repo():
    result = _git("rev-parse", "--is-inside-work-tree")
    if result.returncode != 0:
        print("No git repo found. Initializing...")
        _git_check("init", "init")


def _git_short_log(n=10):
    result = _git("log", "--oneline", "-{}".format(n))
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _revert_files():
    files = CONFIG["modifiable_files"]
    for f in files:
        _git("checkout", "HEAD", "--", f)


def _run_benchmark():
    try:
        result = subprocess.run(
            CONFIG["benchmark_cmd"],
            shell=True,
            capture_output=True,
            text=True,
            timeout=CONFIG["timeout"],
        )
        return result
    except subprocess.TimeoutExpired:
        return None


def _parse_score(stdout):
    lines = stdout.strip().splitlines()
    if not lines:
        return None
    last_line = lines[-1].strip()
    try:
        return float(last_line)
    except ValueError:
        return None


def _format_score(score):
    return "{:.6f}".format(score)


# ---------------------------------------------------------------------------
# Signal handler for Ctrl+C
# ---------------------------------------------------------------------------

_running = True


def _sigint_handler(signum, frame):
    global _running
    _running = False
    print("\nCtrl+C detected. Reverting uncommitted changes...")
    _revert_files()
    state = _load_state()
    print("Reverted. Best score: {} after {} iterations.".format(
        _format_score(state["best_score"]) if state["best_score"] is not None else "N/A",
        state["iteration"],
    ))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_status():
    state = _load_state()
    entries = _read_log()
    improved = [e for e in entries if e.get("result") == "improved"]
    total = len(entries)
    hit_rate = (len(improved) / total * 100) if total > 0 else 0.0

    print("=== autoresearch status ===")
    print("Iterations: {}".format(state["iteration"]))
    print("Best score: {}".format(
        _format_score(state["best_score"]) if state["best_score"] is not None else "N/A"
    ))
    print("Metric: {} ({})".format(CONFIG["metric_name"], CONFIG["metric"]))
    print("Hit rate: {:.1f}% ({}/{})".format(hit_rate, len(improved), total))
    print("")
    log_output = _git_short_log(10)
    if log_output:
        print("Git log (recent):")
        for line in log_output.splitlines():
            print("  {}".format(line))


def cmd_reset():
    if os.path.isfile(STATE_FILE):
        os.remove(STATE_FILE)
    if os.path.isfile(LOG_FILE):
        os.remove(LOG_FILE)
    print("State cleared. .autoresearch/ files removed.")


def cmd_history():
    entries = _read_log()
    if not entries:
        print("No history yet.")
        return
    print("=== improvement history ===")
    for entry in entries:
        result = entry.get("result", "unknown")
        iteration = entry.get("iteration", "?")
        score = entry.get("score")
        prev = entry.get("previous_best")
        if result == "baseline":
            print("  iter-{}: BASELINE {}".format(
                iteration, _format_score(score) if score is not None else "N/A"
            ))
        elif result == "improved":
            print("  iter-{}: IMPROVED {} -> {}".format(
                iteration,
                _format_score(prev) if prev is not None else "N/A",
                _format_score(score) if score is not None else "N/A",
            ))
        elif result == "reverted":
            print("  iter-{}: REVERTED ({})".format(
                iteration,
                _format_score(score) if score is not None else "N/A",
            ))
        elif result == "failed":
            reason = entry.get("reason", "unknown")
            print("  iter-{}: FAILED ({})".format(iteration, reason))
        else:
            print("  iter-{}: {} ({})".format(iteration, result, score))


def cmd_run():
    signal.signal(signal.SIGINT, _sigint_handler)

    _ensure_git_repo()
    _ensure_state_dir()
    state = _load_state()

    iteration = state["iteration"] + 1

    if CONFIG["max_iterations"] > 0 and iteration > CONFIG["max_iterations"]:
        print("Max iterations ({}) reached. Use 'python iterate.py reset' to start over.".format(
            CONFIG["max_iterations"]
        ))
        return

    # Run benchmark
    bench_result = _run_benchmark()

    # Handle timeout
    if bench_result is None:
        print("Benchmark timed out after {}s. Reverting.".format(CONFIG["timeout"]))
        _revert_files()
        log_entry = {
            "iteration": iteration,
            "result": "failed",
            "reason": "timeout",
            "timestamp": time.time(),
        }
        state["iteration"] = iteration
        _save_state(state)
        _append_log(log_entry)
        # Print paste-ready output
        _print_paste_ready(state, "FAILED iter-{}: benchmark timed out".format(iteration))
        return

    # Handle non-zero exit
    if bench_result.returncode != 0:
        stderr_snippet = bench_result.stderr.strip()[:200] if bench_result.stderr else ""
        print("Benchmark failed (exit code {}). Reverting.".format(bench_result.returncode))
        if stderr_snippet:
            print("stderr: {}".format(stderr_snippet))
        _revert_files()
        log_entry = {
            "iteration": iteration,
            "result": "failed",
            "reason": "non_zero_exit",
            "exit_code": bench_result.returncode,
            "stderr": stderr_snippet,
            "timestamp": time.time(),
        }
        state["iteration"] = iteration
        _save_state(state)
        _append_log(log_entry)
        _print_paste_ready(state, "FAILED iter-{}: benchmark exited with code {}".format(
            iteration, bench_result.returncode
        ))
        return

    # Parse score
    score = _parse_score(bench_result.stdout)
    if score is None:
        print("Could not parse score from benchmark output. Reverting.")
        print("stdout (last 5 lines):")
        lines = bench_result.stdout.strip().splitlines()
        for line in lines[-5:]:
            print("  {}".format(line))
        _revert_files()
        log_entry = {
            "iteration": iteration,
            "result": "failed",
            "reason": "unparseable_output",
            "stdout_tail": "\n".join(lines[-5:]),
            "timestamp": time.time(),
        }
        state["iteration"] = iteration
        _save_state(state)
        _append_log(log_entry)
        _print_paste_ready(state, "FAILED iter-{}: could not parse score".format(iteration))
        return

    previous_best = state["best_score"]
    is_baseline = previous_best is None

    if is_baseline:
        # First run -- baseline
        state["best_score"] = score
        state["iteration"] = iteration
        _save_state(state)

        # Git commit baseline (skip if files already committed and clean)
        files = CONFIG["modifiable_files"]
        for f in files:
            _git("add", f)
        # Also stage benchmark.py and program.md if present
        for extra in ["benchmark.py", "program.md"]:
            if os.path.isfile(extra):
                _git("add", extra)
        # Only commit if there are staged changes
        status_result = _git("diff", "--cached", "--quiet")
        if status_result.returncode != 0:
            commit_msg = "iter-{}: baseline {} {}".format(
                iteration, CONFIG["metric_name"], _format_score(score)
            )
            _git_check("commit", "commit", "-m", commit_msg)

        log_entry = {
            "iteration": iteration,
            "result": "baseline",
            "score": score,
            "timestamp": time.time(),
        }
        _append_log(log_entry)

        status_line = "BASELINE iter-{}: {} (first run)".format(
            iteration, _format_score(score)
        )
        _print_paste_ready(state, status_line)

    elif _is_better(score, previous_best):
        # Improved
        state["best_score"] = score
        state["iteration"] = iteration
        _save_state(state)

        files = CONFIG["modifiable_files"]
        for f in files:
            _git("add", f)
        commit_msg = "iter-{}: {} {} -> {}".format(
            iteration,
            CONFIG["metric_name"],
            _format_score(previous_best),
            _format_score(score),
        )
        _git_check("commit", "commit", "-m", commit_msg)

        log_entry = {
            "iteration": iteration,
            "result": "improved",
            "score": score,
            "previous_best": previous_best,
            "timestamp": time.time(),
        }
        _append_log(log_entry)

        status_line = "IMPROVED iter-{}: {} -> {}".format(
            iteration,
            _format_score(previous_best),
            _format_score(score),
        )
        _print_paste_ready(state, status_line)

    else:
        # Worse -- revert
        _revert_files()
        state["iteration"] = iteration
        _save_state(state)

        # Commit a record of the revert
        commit_msg = "iter-{}: reverted ({})".format(
            iteration, _format_score(score)
        )
        # No file changes to commit (reverted), just log
        log_entry = {
            "iteration": iteration,
            "result": "reverted",
            "score": score,
            "previous_best": previous_best,
            "timestamp": time.time(),
        }
        _append_log(log_entry)

        status_line = "REVERTED iter-{}: {} (best remains {})".format(
            iteration,
            _format_score(score),
            _format_score(previous_best),
        )
        _print_paste_ready(state, status_line)


def _print_paste_ready(state, status_line):
    score = state["best_score"]
    score_str = _format_score(score) if score is not None else "N/A"
    files_str = ", ".join(CONFIG["modifiable_files"])

    print("")
    print("Score: {} ({}, {}).".format(score_str, CONFIG["metric_name"], CONFIG["metric"]))
    print(status_line)

    log_output = _git_short_log(5)
    if log_output:
        print("Git log (recent):")
        for line in log_output.splitlines():
            print("  {}".format(line))

    print("Improve {} further. Give me the complete file.".format(files_str))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args:
        cmd_run()
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "reset":
        cmd_reset()
    elif args[0] == "history":
        cmd_history()
    else:
        print("Unknown command: {}".format(args[0]))
        print("Usage: python iterate.py [status|reset|history]")
        sys.exit(1)


if __name__ == "__main__":
    main()
