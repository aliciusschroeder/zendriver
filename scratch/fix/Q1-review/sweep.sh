#!/bin/bash
# runs probe_oneshot_delay.py for delays 0..8 on py3.10 (worktree venv) and py3.13
W=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
P=$S/fix/Q1-review/probe_oneshot_delay.py
cd "$W"
export PYTHONPATH="$W"
for py in "$W/.venv/bin/python" "$S/fix/Q1/venv313/bin/python"; do
  for d in 0 1 2 3 4 5 6 7 8; do
    timeout 30 "$py" "$P" "$d" 2>/dev/null | grep -v "^ *File\|^Traceback" | tr '\n' ' '
    echo
  done
done
