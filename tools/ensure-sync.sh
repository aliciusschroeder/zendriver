#!/usr/bin/env bash
# Start the 5-minute sync loop unless it is already running. Idempotent; called by the
# SessionStart hook (~/.claude/settings.json) and by the supervisor whenever it wakes.
STATE=/home/user/bughunt-state
[ -d "$STATE/tools" ] || exit 0
pid=$(cat /tmp/bughunt-sync.pid 2>/dev/null)
if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && grep -q sync-loop "/proc/$pid/cmdline" 2>/dev/null; then
  echo "bughunt sync loop running (pid $pid)"
  exit 0
fi
setsid nohup bash "$STATE/tools/sync-loop.sh" >/dev/null 2>&1 < /dev/null &
sleep 1
echo "bughunt sync loop started (pid $(cat /tmp/bughunt-sync.pid 2>/dev/null))"
