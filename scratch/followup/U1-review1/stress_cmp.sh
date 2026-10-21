#!/bin/bash
# usage: stress_cmp.sh <fix|base> <310|313> <seed> <runs> [harness]
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/connection/probes
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
BASE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check
cd "$S"
which=$1; v=$2; seed=$3; runs=$4; harness=${5:-stress.py}
if [ "$which" = base ]; then export PYTHONPATH=$BASE:$P; else export PYTHONPATH=$P; fi
if [ "$v" = 313 ]; then py=$S/venv313/bin/python; else py=$W/.venv/bin/python; fi
for i in $(seq 1 "$runs"); do
  timeout 300 "$py" "$P/$harness" "$seed" "${ROUNDS:-200}" 2>&1 | grep -E "^seed|PROBLEM" | cut -c1-220 | tr '\n' ' '
  echo
done
