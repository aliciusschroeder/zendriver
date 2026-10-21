#!/bin/bash
# runs the reviewer's stress harnesses against the worktree's zendriver
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-1
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/connection/probes
V313=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1/venv313
cd "$W"
export PYTHONPATH=$P
for py in "$W/.venv/bin/python" "$V313/bin/python"; do
  echo "=== $py"
  for seed in 0 1 2 3 4 5; do
    NOANS=0 timeout 120 "$py" "$P/stress_domains.py" "$seed" 200 2>&1 | grep -E "^seed|PROBLEM" | sed 's/^/[noans=0] /'
  done
  for seed in 0 1 2; do
    timeout 120 "$py" "$P/stress_domains.py" "$seed" 200 2>&1 | grep -E "^seed|PROBLEM" | sed 's/^/[default] /' | cut -c1-200
  done
  for seed in 0 1 2 3; do
    timeout 180 "$py" "$P/stress.py" "$seed" 200 2>&1 | grep -E "^seed|PROBLEM" | head -5
  done
done
