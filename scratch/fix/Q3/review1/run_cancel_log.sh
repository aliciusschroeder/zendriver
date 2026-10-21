#!/bin/bash
# runs probe_cancel_log.py with python 3.10 (worktree venv) and 3.12 (scratch venv)
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-16
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/review1
cd "$HERE" || exit 1
for py in "$WT/.venv/bin/python" "$HERE/venv312/bin/python" ${EXTRA_PY}; do
    echo "===== $("$py" -c 'import sys; print(sys.version.split()[0])')"
    timeout 60 "$py" -I "$HERE/probe_cancel_log.py" 2>&1 | grep -v "^\s*$" | head -20
done
