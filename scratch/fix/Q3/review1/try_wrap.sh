#!/bin/bash
# applies the coroutine-wrapper variant temporarily, runs the cancel-log probe and the new tests, restores
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-16
HERE=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/review1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
cd "$WT" || exit 1
cp zendriver/core/browser.py "$HERE/browser.py.orig2"
"$WT/.venv/bin/python" "$HERE/patch_wrap.py" zendriver/core/browser.py
EXTRA_PY=$HERE/venv311/bin/python bash "$HERE/run_cancel_log.sh" 2>&1 | grep -E "=====|exception handler|stop\(\) result|atexit kept"
ZENDRIVER_TEST_BROWSERS=headless timeout 300 "$WT/.venv/bin/python" -m pytest tests/core/test_browser.py -p no:cacheprovider -q -rf \
    -k "stopped_responding or drops_while_detaching or concurrent_browser_stop or atexit_cleanup" 2>&1 | grep -E "^FAILED|passed|failed"
cp "$HERE/browser.py.orig2" zendriver/core/browser.py
