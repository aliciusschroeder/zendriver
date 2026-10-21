#!/bin/bash
# runs the given pytest -k expression on python 3.11 (borrowed venv, not re-synced)
cd /home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-4 || exit 1
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
PY=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/fix/Q3-review2/venv3.11/bin/python
K="${K:-keep_a_cancel or retrieve_the_error}"
PYTHONPATH=$PWD ZENDRIVER_TEST_BROWSERS=headless $PY -c "import sys, zendriver; print(sys.version.split()[0], zendriver.__file__)"
PYTHONPATH=$PWD ZENDRIVER_TEST_BROWSERS=headless $PY -m pytest tests/core/test_tab.py tests/core/test_cloudflare.py -p no:cacheprovider -q -rf -k "$K" 2>&1 | grep -E "^FAILED|passed|failed"
