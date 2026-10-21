#!/bin/bash
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/lifecycle/probes
cd "$S"
for py in "$S/venv313/bin/python" "$W/.venv/bin/python"; do
  for i in 1 2; do
    echo "=== $py run $i"
    timeout 200 "$py" "$P/concurrent_stop_plain.py" 2>&1 | tail -7
  done
done
