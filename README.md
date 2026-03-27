# karpathy-loop

A zero-dependency Python + git ratchet for autonomous iterative code improvement. Claude Code reads a `program.md` instruction file describing what to optimize, generates improved code, and `iterate.py` handles benchmarking, scoring, and git commit/revert decisions. No API keys. No pip installs. Pure Python stdlib + git. The score can only go up (or down, depending on direction) -- failed experiments are automatically reverted, and every improvement is committed with its score delta in the message.

## Requirements

- **Python 3.8+**
- **git** (any recent version)
- **numpy** (for the SMC example only -- the core tool has zero dependencies)
- **Claude Code** with a Max plan (for the autonomous loop)

## Quick Start

Run the included SMC controller optimization example in 3 commands:

```bash
cd examples/smc
python benchmark.py          # verify it runs, prints a float
python iterate.py             # establishes baseline, commits it
```

After the baseline is established, open Claude Code in `examples/smc/` and tell it to read `program.md` and start optimizing. It will modify `controllers/surface.py`, run `python iterate.py`, read the output, and loop.

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

The output of `iterate.py` is designed to be paste-ready for Claude Code. It prints the current best score, the result of the last iteration (BASELINE, IMPROVED, REVERTED, or FAILED), the recent git log, and a prompt asking for the next improvement. Claude Code reads this and generates the next version.

## Use on Your Own Project

### Option A: Manual setup (4 steps)

1. Copy `iterate.py` into your project directory
2. Edit the 4 CONFIG lines at the top:

```python
CONFIG = {
    "benchmark_cmd": "python benchmark.py",
    "modifiable_files": ["src/my_algorithm.py"],
    "metric": "minimize",          # "minimize" or "maximize"
    "metric_name": "Mean ISE",
}
```

3. Write a `benchmark.py` that evaluates your code and prints a single float as the last line of stdout
4. Write a `program.md` that tells Claude Code what the goal is, what files it can change, and any constraints

### Option B: Use the scaffolder

```bash
python setup_project.py
```

This interactively prompts for your project name, metric, direction, benchmark command, and modifiable files, then generates a ready-to-go project directory with `iterate.py` (pre-configured), `benchmark.py` (template), `program.md` (template), and `.gitignore`.

## Commands

| Command | Description |
|---|---|
| `python iterate.py` | Run one iteration: benchmark, compare, commit or revert |
| `python iterate.py status` | Show current best score, iteration count, and hit rate |
| `python iterate.py history` | Show full improvement history (BASELINE, IMPROVED, REVERTED, FAILED) |
| `python iterate.py reset` | Clear state files in `.autoresearch/` to start over |

## Writing a Good benchmark.py

- Must print a **single float as the last line** of stdout. `iterate.py` parses `float(last_line)`.
- Can print diagnostic info on earlier lines -- only the last line matters.
- Must exit with code 0 on success. Non-zero exit = automatic revert.
- Should run in under 5 minutes (configurable via `CONFIG["timeout"]`).
- Should be deterministic. If it uses randomness, fix the seed.
- Test multiple scenarios if possible (the SMC example tests 3 different plants and averages the ISE).

## Writing a Good program.md

- State the goal clearly: what metric, which direction, what file to modify.
- List hard constraints: required class/function signatures, allowed imports, line limits.
- Describe the domain: what the code does, what the plants/environments are.
- Include strategy hints: what knobs exist, what tradeoffs to explore.
- Mention what NOT to do: avoid breaking changes, keep the API stable.

See `examples/smc/program.md` and `examples/twb/program.md` for reference.

## File Structure

```
karpathy-loop/
  iterate.py              Core ratchet tool (copy into any project)
  setup_project.py        Interactive project scaffolder
  .gitignore              Standard ignores
  examples/
    smc/                  SMC controller optimization (uses numpy)
      benchmark.py          Simulates 3 plants, prints mean ISE
      program.md            Instructions for Claude Code
      controllers/
        surface.py            Modifiable: the SMC controller
    twb/                  Two-wheeled balancing robot (stdlib only)
      benchmark.py          Simulates inverted pendulum, prints score
      program.md            Instructions for Claude Code
      controller/
        balance.py            Modifiable: the PID controller
```

## License

MIT
