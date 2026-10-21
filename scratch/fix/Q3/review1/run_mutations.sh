#!/bin/bash
# runs the new stop() tests against single-hunk reverts of the fix
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-16
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/review1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd "$WT" || exit 1
cp zendriver/core/browser.py "$HERE/browser.py.orig"
for m in M1 M2 M3 M4 M5 M6; do
    cp "$HERE/browser.py.orig" zendriver/core/browser.py
    uv run python "$HERE/mutate.py" zendriver/core/browser.py "$m" 2>/dev/null
    echo "== $m"
    timeout 300 uv run pytest tests/core/test_browser.py -p no:cacheprovider -q -rf \
        -k "stopped_responding or drops_while_detaching or concurrent_browser_stop or atexit_cleanup" 2>&1 \
        | grep -E "^FAILED|passed|failed"
done
cp "$HERE/browser.py.orig" zendriver/core/browser.py
