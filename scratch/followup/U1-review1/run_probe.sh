#!/bin/bash
# usage: run_probe.sh <fix|base> <310|313> <probe path> [args...]
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/connection/probes
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
BASE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check
cd "$S"
which=$1; v=$2; probe=$3; shift 3
if [ "$which" = base ]; then export PYTHONPATH=$BASE:$P; else export PYTHONPATH=$P; fi
if [ "$v" = 313 ]; then py=$S/venv313/bin/python; else py=$W/.venv/bin/python; fi
timeout 120 "$py" "$probe" "$@" 2>&1
