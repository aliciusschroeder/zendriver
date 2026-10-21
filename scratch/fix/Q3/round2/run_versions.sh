#!/bin/bash
# runs the affected test modules with the python 3.11 and 3.12 venvs
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-26
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/round2
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd "$WT" || exit 1
for v in 311 312; do
    PY="$HERE/venv$v/bin/python"
    "$PY" -c "import sys, zendriver; print(sys.version.split()[0], zendriver.__file__)"
    ZENDRIVER_TEST_BROWSERS=headless timeout 900 "$PY" -m pytest "$@" -p no:cacheprovider -q 2>&1 | tail -2
done
