#!/usr/bin/env python3
"""Print the completed agent results of a workflow journal as JSON.

  python3 journal_results.py <journal.jsonl> [--labels-only]

Output: [{"label": ..., "phase": ..., "agentId": ..., "result": ...}, ...] for every agent
that finished, plus {"in_flight": [labels...]} for agents that started but never returned.
Use it to continue a half-done workflow in a new session (resumeFromRunId only works in
the session that ran it): run the stage script for the missing labels only.
"""
import json
import sys

path = sys.argv[1]
started, done = {}, []
for line in open(path):
    try:
        d = json.loads(line)
    except ValueError:
        continue
    if d.get("type") == "started":
        started[d["key"]] = d
    elif d.get("type") == "result":
        s = started.get(d["key"], {})
        done.append({"label": s.get("label"), "phase": s.get("phase"), "agentId": d.get("agentId"), "result": d.get("result")})
finished = {d["key"] for d in map(json.loads, open(path)) if d.get("type") == "result"}
in_flight = [s.get("label") for k, s in started.items() if k not in finished]
if "--labels-only" in sys.argv:
    print(json.dumps({"done": [d["label"] for d in done], "in_flight": in_flight}, indent=1))
else:
    print(json.dumps({"done": done, "in_flight": in_flight}, indent=1))
