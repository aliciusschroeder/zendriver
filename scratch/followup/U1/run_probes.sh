#!/bin/bash
# runs the reviewer probes against the worktree's zendriver on 3.10 and 3.13
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-1
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review
V313=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1/venv313
cd "$W"
for py in "$W/.venv/bin/python" "$V313/bin/python"; do
  echo "=== $py"
  for f in cancellation/probe_fake_dialog_wedge.py connection/probes/probe_routed_then_fail.py connection/probes/probe_failed_then_sent2.py connection/probes/probe_manual_enable_cancel.py; do
    echo "--- $f"
    PYTHONPATH=$P/connection/probes timeout 30 "$py" "$P/$f" 2>&1 | tail -6
  done
done
