#!/bin/bash
# run the delay probe on py3.13 and py3.10 with the given delays against this worktree
W=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
cd "$W"
export PYTHONPATH="$W"
for d in "$@"; do
  timeout 30 "$S/fix/Q1/venv313/bin/python" "$S/fix/Q1-review/probe_oneshot_delay.py" "$d" 2>/dev/null | grep -v "^ *File\|^Traceback" | tr '\n' ' '
  echo
done
