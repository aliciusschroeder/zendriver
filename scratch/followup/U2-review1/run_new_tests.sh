#!/bin/bash
# runs the new U2 tests (or the -k expression given) on 3.10 and 3.13
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-4 || exit 1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
K="${K:-keep_a_cancel or retrieve_the_error}"
FILES="${FILES:-tests/core/test_tab.py tests/core/test_cloudflare.py}"
echo "== 3.10"
ZENDRIVER_TEST_BROWSERS=headless uv run pytest $FILES -p no:cacheprovider -q -rf -k "$K" 2>&1 | grep -E "^FAILED|passed|failed"
echo "== 3.13"
UV_PROJECT_ENVIRONMENT=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U2-review1/venv313 ZENDRIVER_TEST_BROWSERS=headless uv run pytest $FILES -p no:cacheprovider -q -rf -k "$K" 2>&1 | grep -E "^FAILED|passed|failed"
