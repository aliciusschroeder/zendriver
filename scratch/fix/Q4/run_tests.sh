#!/usr/bin/env bash
# runs the given pytest args in the Q4 worktree with Chromium on PATH
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-4 || exit 1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
exec timeout 900 uv run pytest -p no:cacheprovider -q "$@"
