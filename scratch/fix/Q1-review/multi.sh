#!/bin/bash
# usage: multi.sh <pytest args...>; runs tests 3x on py3.11/3.12/3.13 against this worktree
W=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-14
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q1
cd "$W"
export PYTHONPATH="$W"
for v in venv311 venv312 venv313; do
  echo "== $v"
  for i in 1 2 3; do
    "$S/$v/bin/python" -m pytest "$@" -p no:cacheprovider -q 2>&1 | tail -1
  done
done
