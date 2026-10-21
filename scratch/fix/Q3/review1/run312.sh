#!/bin/bash
# runs the new stop() tests 3 times under python 3.12
WT=/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-16
V=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3/review1/venv312/bin/python
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd "$WT" || exit 1
"$V" -c "import sys, zendriver; print(sys.version, zendriver.__file__)"
K="stopped_responding or drops_while_detaching or concurrent_browser_stop or atexit_cleanup"
if [ "$1" = "full" ]; then
    timeout 600 "$V" -m pytest tests/core/test_browser.py tests/core/test_connection.py -p no:cacheprovider -q -rf 2>&1 | grep -E "^FAILED|passed|failed"
    exit
fi
for i in 1 2 3; do
    timeout 300 "$V" -m pytest tests/core/test_browser.py -p no:cacheprovider -q -rf -k "$K" 2>&1 | grep -E "^FAILED|passed|failed"
done
