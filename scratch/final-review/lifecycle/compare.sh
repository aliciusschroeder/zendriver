#!/bin/bash
L=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/lifecycle
PY310=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check/.venv/bin/python
until [ -f $L/logs/loop.done ]; do sleep 5; done
nohup taskset -c 0 /home/user/zendriver/.venv/bin/python $L/cpuhog.py 4 1200 $L/hog2.pid >/dev/null 2>&1 &
sleep 1
for i in 1 2 3 4 5; do
  TREE=base $L/runsuite.sh $PY310 cmp-base310-$i -n 4 tests/core
  TREE=run  $L/runsuite.sh $PY310 cmp-tip310-$i -n 4 tests/core
done
kill $(cat $L/hog2.pid) 2>/dev/null
echo CMPDONE > $L/logs/cmp.done
