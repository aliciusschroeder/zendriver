#!/bin/bash
# usage: run_probe.sh <probe.py> <args...>
# Runs the probe in a child interpreter with TMPDIR pointing at our scratch tmp,
# then checks (after the interpreter has exited) whether the spawned chrome and
# its profile survived. Cleans up only processes whose cmdline names OUR tmpdir.
D=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/verify/Q4-reproduce
export PATH=/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/bin:$PATH
PIDFILE=$D/pids.$$.txt
rm -f "$PIDFILE"
PY=/home/user/zendriver/.venv/bin/python
probe=$1; shift
cd "$D"
timeout 120 $PY "$D/$probe" "$@" "$PIDFILE"
echo "probe exit code: $?"
sleep ${SLEEP:-3}
echo "=== ${SLEEP:-3}s after the interpreter exited ==="
if [ -f "$PIDFILE" ]; then
  while read -r pid prof; do
    if [ -d /proc/$pid ]; then
      echo "pid $pid ALIVE: $(ps -o pid=,ppid=,stat=,etime= -p $pid)  (comm $(cat /proc/$pid/comm))"
    else
      echo "pid $pid gone"
    fi
    if [ -n "$prof" ]; then
      [ -d "$prof" ] && echo "profile $prof EXISTS" || echo "profile $prof removed"
    fi
  done < "$PIDFILE"
fi
# cleanup: only OUR processes (cmdline names the exact profile our probe spawned)
if [ -f "$PIDFILE" ]; then
  while read -r pid prof; do
    n=$(pgrep -f -- "--user-data-dir=$prof( |$)" | wc -l)
    echo "processes using profile $prof: $n"
    pkill -KILL -f -- "--user-data-dir=$prof( |$)" 2>/dev/null
    sleep 1
    echo "after cleanup: $(pgrep -f -- "--user-data-dir=$prof( |$)" | wc -l) left"
    case "$prof" in /tmp/uc_*) rm -rf "$prof";; esac
  done < "$PIDFILE"
fi
rm -f "$PIDFILE"
