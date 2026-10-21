#!/bin/bash
# applies each mutation to the worktree's browser.py, runs the stop tests and restores the file
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-26
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/round2
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd "$WT" || exit 1
cp zendriver/core/browser.py "$HERE/browser.py.fixed"
for m in unbounded_forwarders forwarders_before_process gather_to_wait_for unguarded_process_reset; do
    uv run python "$HERE/mutate.py" "$WT" "$m" 2>&1 | grep applied
    ZENDRIVER_TEST_BROWSERS=headless timeout 300 uv run pytest tests/core/test_browser.py -p no:cacheprovider -q \
        -k "stopped_responding or connection_drops or concurrent_browser_stop or unretrieved or proxy_forwarders or started_while or atexit_cleanup" \
        2>&1 | grep -E "^FAILED|passed|failed"
    cp "$HERE/browser.py.fixed" zendriver/core/browser.py
done
cmp "$HERE/browser.py.fixed" zendriver/core/browser.py && echo restored
