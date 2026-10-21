#!/bin/bash
# tests/core/test_connection.py on py3.13 against this worktree
W=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
cd "$W"
export PYTHONPATH="$W"
timeout 300 "$S/fix/Q1/venv313/bin/python" -m pytest tests/core/test_connection.py -p no:cacheprovider -q -W ignore -rf --tb=line 2>&1 | grep -E "^E |Error|passed|failed" | grep -v "^  " | tail -20
