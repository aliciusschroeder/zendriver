#!/bin/bash
# reruns the cross-site frame test several times on the given python env
# usage: frames_repeat.sh <venv dir or "" for the worktree .venv> <runs>
W=/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd "$W"
if [ -n "$1" ]; then export UV_PROJECT_ENVIRONMENT="$1"; fi
T="tests/core/test_frames.py"
for i in $(seq 1 "$2"); do
  timeout 300 uv run pytest -p no:cacheprovider -q -n 4 "$T" "$T" "$T" "$T" 2>&1 | grep -E "^E  .{0,200}$|^FAILED|passed|failed" | head -12
done
