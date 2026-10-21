#!/bin/bash
# run a command in the Q2 worktree with chromium on PATH
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-25 || exit 1
exec "$@"
