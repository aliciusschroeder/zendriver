#!/usr/bin/env bash
# usage: run_tests_py.sh <python-version> <pytest args...>
# runs pytest in the Q4 worktree with a per-version venv kept in the scratchpad
cd /home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-4 || exit 1
ver=$1
shift
export UV_PROJECT_ENVIRONMENT=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q4/venv$ver
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
exec timeout 900 uv run --python "$ver" --all-groups pytest -p no:cacheprovider -q "$@"
