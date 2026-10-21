#!/usr/bin/env bash
# usage: run_tests.sh <pytest args...>
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-11 || exit 1
timeout 900 uv run pytest -p no:cacheprovider -q "$@" 2>&1 | grep -v UV_NATIVE
