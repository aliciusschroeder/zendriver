#!/usr/bin/env bash
# Runs tools/sync.py every 5 minutes. Started (detached) by tools/ensure-sync.sh.
STATE=/home/user/bughunt-state
echo $$ > /tmp/bughunt-sync.pid
while true; do
  flock -n /tmp/bughunt-sync.lock python3 "$STATE/tools/sync.py" >> /tmp/bughunt-sync.out 2>&1
  sleep "${BUGHUNT_SYNC_INTERVAL:-300}"
done
