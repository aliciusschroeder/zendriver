#!/bin/bash
# usage: clean_end.sh <fix|base> <310|313> <first> <last>
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
BASE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check
cd "$S/probes"
if [ "$1" = base ]; then export PYTHONPATH=$BASE:$S/probes; else export PYTHONPATH=$S/probes; fi
if [ "$2" = 313 ]; then py=$S/venv313/bin/python; else py=$W/.venv/bin/python; fi
for seed in $(seq "$3" "$4"); do
  out=$(timeout 300 "$py" "$S/probes/stress_clean_end.py" "$seed" 200 2>&1)
  echo "$(echo "$out" | grep -E '^seed') $(echo "$out" | grep -E 'PROBLEM' | tr '\n' ' ' | cut -c1-400)"
done
