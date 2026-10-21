#!/bin/bash
# usage: diag_loop.sh <fix|base> <310|313> <seed> <max runs>
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
BASE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check
cd "$S/probes"
which=$1; v=$2; seed=$3; runs=$4
if [ "$which" = base ]; then export PYTHONPATH=$BASE:$S/probes; else export PYTHONPATH=$S/probes; fi
if [ "$v" = 313 ]; then py=$S/venv313/bin/python; else py=$W/.venv/bin/python; fi
for i in $(seq 1 "$runs"); do
  out=$(timeout 300 "$py" "$S/probes/stress_diag.py" "$seed" "${ROUNDS:-200}" 2>&1)
  echo "run $i: $(echo "$out" | grep -E '^seed')"
  if echo "$out" | grep -q DIAG; then
    echo "$out" | grep -E "DIAG|PROBLEM" | cut -c1-1500
    true
  fi
done
