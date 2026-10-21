#!/bin/bash
# usage: run_suite.sh <310|313> [pytest args...]
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5 || exit 1
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
v=$1; shift
if [ "$v" = 313 ]; then
  export UV_PROJECT_ENVIRONMENT=$S/venv313
fi
timeout 1200 uv run pytest "$@" -p no:cacheprovider -q 2>&1 | grep -v UV_NATIVE | tail -25
