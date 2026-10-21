#!/bin/bash
# runsuite.sh <python> <label> [extra pytest args]
L=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/lifecycle
PY=$1; LABEL=$2; shift 2
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
export ZENDRIVER_TEST_BROWSERS=headless
cd $L/${TREE:-run}
PYTHONPATH=$L/${TREE:-run} $PY -c "import zendriver;print(zendriver.__file__)" > $L/logs/$LABEL.txt
PYTHONPATH=$L/${TREE:-run} timeout 900 $PY -m pytest --rootdir $L/${TREE:-run} -p no:cacheprovider -o asyncio_mode=auto -q -rfEs "$@" >> $L/logs/$LABEL.txt 2>&1
echo "exit=$?" >> $L/logs/$LABEL.txt
