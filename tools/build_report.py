#!/usr/bin/env python3
"""Build the per-group part of the final report from the stage outputs."""
import json, subprocess, sys
SCR = "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad"
sys.path.insert(0, SCR + "/triage")
from spec import GROUPS, DROPPED, SEEDS  # noqa: E402

F = {f["fid"]: f for f in json.load(open(SCR + "/findings_flat.json"))}
s3 = {g["group_id"]: g for g in json.load(open(SCR + "/stage3.json"))["groups"]}
s4 = {r["group"]: r for r in json.load(open(SCR + "/stage4.json"))["results"]}
REPO = "/home/user/zendriver"
merges = subprocess.run(["git", "-C", REPO, "log", "--merges", "--format=%h %s", "064148f..HEAD"], capture_output=True, text=True).stdout.splitlines()

def where(fid):
    if fid in F:
        f = F[fid]
        return f"{f['file']}:{f['function']}:{f['line']}"
    return "(seeded lead)"

def votes(gid):
    g = s3[gid]
    return "".join({"confirmed": "C", "partially-confirmed": "P", "refuted": "R"}.get(v["verdict"], "?") for v in g["votes"])

def member_note(gid):
    t = s3[gid]["memberTally"]
    bad = [f"{k} {v['confirmed']}/3" for k, v in t.items() if v["confirmed"] < 3]
    return ("; members not confirmed 3/3: " + ", ".join(bad)) if bad else ""

out = []
for g in GROUPS:
    gid = g["id"]
    first = next((m for m in g["members"] if m in F), g["members"][0])
    line = f"### {gid} {g['slug']}\n"
    if g["queue"] == "fix":
        r = s4[gid]
        last = r["rounds"][-1]["fix"]
        merge = next((m.split()[0] for m in merges if f"fix/{g['slug']}:" in m), "?")
        status = "fixed" if r["status"] == "APPROVED" else "blocked"
        subject = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%s", r["commit"]], capture_output=True, text=True).stdout.strip()
        files = ", ".join(f for f in last["files_changed"] if f.startswith("zendriver"))
        line += (f"- status: **{status}** (verify {votes(gid)}{member_note(gid)}; review approved in round {len(r['rounds'])})\n"
                 f"- evidence: {where(first)}; members {', '.join(g['members'])}\n"
                 f"- patch: {subject} ({files}); commit {r['commit'][:9]} on fix/{g['slug']}, merged as {merge}\n"
                 f"- tests added ({len(last['tests_added'])}): " + ", ".join(t.split('::')[-1] for t in last["tests_added"]) + "\n")
    else:
        kind = "report-only (design/API change)" if g["queue"] == "design" else "report-only (below the fix cap)"
        line += (f"- status: **{kind}** (verify {votes(gid)}{member_note(gid)})\n"
                 f"- evidence: {where(first)}; members {', '.join(g['members'])}\n"
                 f"- finding: {g['title']}\n")
    out.append(line)
if "--table" not in sys.argv:
    print("\n".join(out))


def table():
    fu = {r["unit"]: r for r in json.load(open(SCR + "/followup.json"))["results"]}
    rows = ["| group | status | evidence (file:function:line) | patch / commit | tests |", "|---|---|---|---|---|"]
    for g in GROUPS:
        gid = g["id"]
        first = next((m for m in g["members"] if m in F), None)
        ev = where(first) if first else "seeded: " + g["files"].split(" (")[0]
        ev = ev.replace("zendriver/core/", "")
        if g["queue"] == "fix":
            r = s4[gid]
            subject = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%s", r["commit"]], capture_output=True, text=True).stdout.strip()
            merge = next((m.split()[0] for m in merges if f"fix/{g['slug']}:" in m), "?")
            n = len(r["rounds"][-1]["fix"]["tests_added"])
            st = "fixed" if r["status"] == "APPROVED" else "BLOCKED"
            rows.append(f"| {gid} {g['slug']} | {st} | {ev} | {subject} — {r['commit'][:7]} (merge {merge}) | {n} |")
        else:
            st = "report-only (design)" if g["queue"] == "design" else "report-only"
            rows.append(f"| {gid} {g['slug']} | {st} | {ev} | — | — |")
    names = {"U1": "final-review follow-up: connection (send/rollback/session failure)", "U2": "final-review follow-up: cancellation-safe timeout bounds", "U3": "final-review follow-up: concurrent stop with proxies + test sync"}
    for uid, r in fu.items():
        subject = subprocess.run(["git", "-C", REPO, "log", "-1", "--format=%s", r["commit"]], capture_output=True, text=True).stdout.strip()
        merge = next((m.split()[0] for m in merges if f"fix/{r['slug']}:" in m), "?")
        n = len(r["rounds"][-1]["fix"]["tests_added"])
        rows.append(f"| {uid} {r['slug']} | fixed | {names[uid]} | {subject} — {r['commit'][:7]} (merge {merge}) | {n} |")
    return "\n".join(rows)


if __name__ == "__main__" and "--table" in sys.argv:
    print(table())
