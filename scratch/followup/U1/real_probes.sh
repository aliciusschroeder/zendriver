#!/bin/bash
# runs the reviewer's real-Chromium dialog probes against the worktree's zendriver
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-1
P=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/cancellation
V313=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1/venv313
export CHROME=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin/chromium
cd "$W"
echo "=== 3.13 log select"
timeout 60 "$V313/bin/python" "$P/probe_dialog_recover.py" log select 2>&1 | grep -vE "^  \[" | tail -12
echo "=== 3.10 runtime select"
timeout 60 "$W/.venv/bin/python" "$P/probe_dialog_recover.py" runtime select 2>&1 | grep -vE "^  \[" | tail -12
echo "=== 3.13 expect_dialog"
timeout 60 "$V313/bin/python" "$P/probe_expect_dialog.py" 2>&1 | tail -12
