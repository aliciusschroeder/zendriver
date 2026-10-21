#!/bin/bash
# runs test_frames.py N times on 3.13 and 3.10
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5 || exit 1
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1
N=${1:-5}
for i in $(seq 1 "$N"); do
  echo "3.13 run $i: $(UV_PROJECT_ENVIRONMENT=$S/venv313 timeout 600 uv run pytest tests/core/test_frames.py -p no:cacheprovider -q -n 4 2>&1 | grep -E 'passed|failed|FAILED' | tr '\n' ' ')"
  echo "3.10 run $i: $(timeout 600 uv run pytest tests/core/test_frames.py -p no:cacheprovider -q -n 4 2>&1 | grep -E 'passed|failed|FAILED' | tr '\n' ' ')"
done
