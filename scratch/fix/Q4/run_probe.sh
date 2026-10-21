#!/usr/bin/env bash
# runs the real-Chromium probe with the Q4 worktree's zendriver
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-4 || exit 1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
exec timeout 300 uv run python /tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q4/probe_real.py
