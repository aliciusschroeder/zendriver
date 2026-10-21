#!/bin/bash
# runs the reviewer's stress_domains harness against this worktree, default NOANS
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/connection/probes
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
cd "$S"
export PYTHONPATH=$P
ROUNDS=${ROUNDS:-200}
for py in "$W/.venv/bin/python" "$S/venv313/bin/python"; do
  echo "=== $py"
  for seed in $SEEDS; do
    timeout 300 "$py" "$P/${HARNESS:-stress_domains.py}" "$seed" "$ROUNDS" 2>&1 | grep -E "^seed|PROBLEM" | cut -c1-220
  done
done
