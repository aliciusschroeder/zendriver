#!/bin/bash
S=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/BB-fixsafety
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd $S/suite
for g in base R26 R27 R30 R42; do
  echo "=== $g" 
  PYTHONPATH=$S/$g/pkg timeout 900 /home/user/zendriver/.venv/bin/python -m pytest --rootdir $S/suite -p no:cacheprovider -m "not external" tests/core/test_tab.py tests/core/test_connection.py -q -o console_output_style=classic 2>&1 | grep -E "passed|failed|FAILED|ERROR|error" | tail -15
done
