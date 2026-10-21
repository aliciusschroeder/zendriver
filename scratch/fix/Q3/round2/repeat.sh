#!/bin/bash
# runs the stop tests 3 times serially, then the core suite with xdist
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-26
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd "$WT" || exit 1
K="stopped_responding or connection_drops or concurrent_browser_stop or unretrieved or proxy_forwarders or started_while or atexit_cleanup"
for i in 1 2 3; do
    timeout 600 uv run pytest tests/core/test_browser.py -p no:cacheprovider -q -k "$K" 2>&1 | tail -1
done
for i in 1 2; do
    timeout 600 uv run pytest tests/core/test_browser.py tests/core/test_connection.py tests/core/test_proxy.py -p no:cacheprovider -q -n 3 2>&1 | tail -1
done
timeout 1200 uv run pytest tests/core -p no:cacheprovider -q -n 3 2>&1 | tail -3
