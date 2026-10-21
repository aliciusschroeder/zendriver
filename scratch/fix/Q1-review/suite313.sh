#!/bin/bash
# full headless suite on py3.13 against this worktree
W=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad
cd "$W"
export PYTHONPATH="$W"
export PATH="$S/bin:$PATH"
export ZENDRIVER_TEST_BROWSERS=headless
timeout 600 "$S/fix/Q1/venv313/bin/python" -m pytest -n 4 -p no:cacheprovider -q 2>&1 | tail -2
