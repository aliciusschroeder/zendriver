#!/bin/bash
L=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/final-review/lifecycle
IDS=$(cat /tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/integration/ids-new.txt | tr '\n' ' ')
for i in $(seq 1 8); do
  $L/runsuite.sh /home/user/zendriver/.venv/bin/python loop313-full-$i -n 4
  $L/runsuite.sh /tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/flaky-check/.venv/bin/python loop310-full-$i -n 4
done
echo LOOPDONE > $L/logs/loop.done
