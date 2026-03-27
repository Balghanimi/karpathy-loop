"""
setup_project.py -- Interactive scaffolder for new karpathy-loop projects.

Prompts for project settings, then creates a project directory with:
  - iterate.py   (patched copy of the real iterate.py with CONFIG filled in)
  - benchmark.py  (template)
  - program.md    (template)
  - .gitignore    (standard karpathy-loop ignores)

Zero dependencies beyond Python stdlib.
"""

import os
import re
import sys
import textwrap


def _locate_iterate():
    """Find iterate.py in the same directory as this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, "iterate.py")
    if not os.path.isfile(path):
        print("Error: iterate.py not found at {}".format(path))
        sys.exit(1)
    return path


def _read_iterate(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _patch_config(source, benchmark_cmd, modifiable_files, metric, metric_name):
    """Replace the CONFIG dict block in iterate.py source with user values.

    Matches everything from the '# CONFIG' comment header through the
    closing brace of the CONFIG dict.
    """
    files_list = ", ".join('"{}"'.format(f.strip()) for f in modifiable_files)

    new_config = textwrap.dedent("""\
        # ---------------------------------------------------------------------------
        # CONFIG -- edit these for your project
        # ---------------------------------------------------------------------------
        CONFIG = {{
            "benchmark_cmd": "{benchmark_cmd}",
            "modifiable_files": [{files_list}],
            "metric": "{metric}",{metric_pad}# "minimize" or "maximize"
            "metric_name": "{metric_name}",
            "timeout": 300,                # seconds
            "max_iterations": 50,          # 0 = unlimited
        }}""").format(
        benchmark_cmd=benchmark_cmd,
        files_list=files_list,
        metric=metric,
        metric_pad="          " if metric == "minimize" else "         ",
        metric_name=metric_name,
    )

    # Match from the CONFIG comment header to the closing brace + newline
    pattern = (
        r"# -{10,}\n"
        r"# CONFIG -- edit these for your project\n"
        r"# -{10,}\n"
        r"CONFIG\s*=\s*\{[^}]*\}"
    )
    patched, count = re.subn(pattern, new_config, source, count=1, flags=re.DOTALL)
    if count == 0:
        print("Error: could not find CONFIG dict in iterate.py to patch.")
        sys.exit(1)
    return patched


def _prompt(label, default=None, required=False):
    """Prompt user for input with optional default."""
    if default is not None:
        prompt_str = "{} [{}]: ".format(label, default)
    else:
        prompt_str = "{}: ".format(label)

    while True:
        value = input(prompt_str).strip()
        if not value and default is not None:
            return default
        if not value and required:
            print("  This field is required.")
            continue
        if value:
            return value


def _write_file(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


BENCHMARK_TEMPLATE = textwrap.dedent("""\
    \"\"\"
    benchmark.py -- Evaluate the current solution and print a single float.

    The last line of stdout must be a single float (the score).
    iterate.py reads this to decide whether to keep or revert changes.
    \"\"\"


    def evaluate():
        # TODO: implement your evaluation logic here
        # Must return a float score
        raise NotImplementedError("Implement evaluate() to return a float score")


    if __name__ == "__main__":
        score = evaluate()
        print(score)
""")


PROGRAM_MD_TEMPLATE = textwrap.dedent("""\
    # {project_name}

    ## Goal
    <!-- Describe what you are trying to achieve -->

    ## Approach
    <!-- Describe the method or algorithm -->

    ## Constraints
    <!-- Any constraints on the solution -->

    ## Metric
    - **Name:** {metric_name}
    - **Direction:** {metric}
    - **Benchmark:** `{benchmark_cmd}`

    ## Files
    - **Modifiable:** {files_str}
    - **Benchmark:** benchmark.py

    ## Notes
    <!-- Any additional context for the autonomous loop -->
""")


GITIGNORE_TEMPLATE = textwrap.dedent("""\
    .karpathy-loop/
    __pycache__/
    *.pyc
    .env
    *.log
""")


def main():
    print("=== karpathy-loop project scaffolder ===")
    print("")

    project_name = _prompt("Project name", required=True)
    metric_name = _prompt("Metric name", default="Score")

    while True:
        metric = _prompt("Direction (minimize/maximize)", default="minimize")
        if metric in ("minimize", "maximize"):
            break
        print("  Must be 'minimize' or 'maximize'.")

    benchmark_cmd = _prompt("Benchmark command", default="python benchmark.py")
    files_raw = _prompt("Modifiable file(s) (comma-separated)", required=True)
    modifiable_files = [f.strip() for f in files_raw.split(",") if f.strip()]

    if not modifiable_files:
        print("Error: at least one modifiable file is required.")
        sys.exit(1)

    # Create project directory
    project_dir = os.path.abspath(project_name)
    if os.path.exists(project_dir):
        print("Error: directory already exists: {}".format(project_dir))
        sys.exit(1)

    os.makedirs(project_dir, exist_ok=True)

    # Read and patch iterate.py
    iterate_path = _locate_iterate()
    iterate_source = _read_iterate(iterate_path)
    patched = _patch_config(
        iterate_source, benchmark_cmd, modifiable_files, metric, metric_name
    )
    _write_file(os.path.join(project_dir, "iterate.py"), patched)

    # Write benchmark.py
    _write_file(os.path.join(project_dir, "benchmark.py"), BENCHMARK_TEMPLATE)

    # Write program.md
    files_str = ", ".join("`{}`".format(f) for f in modifiable_files)
    program_content = PROGRAM_MD_TEMPLATE.format(
        project_name=project_name,
        metric_name=metric_name,
        metric=metric,
        benchmark_cmd=benchmark_cmd,
        files_str=files_str,
    )
    _write_file(os.path.join(project_dir, "program.md"), program_content)

    # Write .gitignore
    _write_file(os.path.join(project_dir, ".gitignore"), GITIGNORE_TEMPLATE)

    # Print summary
    print("")
    print("Created {}/".format(project_name))
    print("  |- iterate.py          (configured with your settings)")
    print("  |- benchmark.py        (template -- implement evaluate())")
    print("  |- program.md          (describe your project goals here)")
    print("  |- .gitignore")
    print("")
    print("Next steps:")
    print("  1. cd {}".format(project_name))
    print("  2. Implement benchmark.py (must print a single float as last line)")
    for f in modifiable_files:
        print("  3. Create your modifiable file: {}".format(f))
    print("  4. Run: python iterate.py          (establishes baseline)")
    print("  5. Let Claude Code read program.md and run the autonomous loop")


if __name__ == "__main__":
    main()
