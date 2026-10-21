#!/bin/bash
# real Chromium: two lazily enabled handler domains while an alert blocks the page
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export CHROME=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin/chromium
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
cd "$S"
echo "=== 3.13 log,network select"
timeout 90 "$S/venv313/bin/python" "$S/probes/probe_dialog_recover_multi.py" log,network select 2>&1 | tail -14
echo "=== 3.10 runtime,log select"
timeout 90 "$W/.venv/bin/python" "$S/probes/probe_dialog_recover_multi.py" runtime,log select 2>&1 | tail -14
