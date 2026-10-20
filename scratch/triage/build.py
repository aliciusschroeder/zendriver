import json, sys
sys.path.insert(0, '.')
from spec import SEEDS, GROUPS, DROPPED
F = {f['fid']: f for f in json.load(open('../findings_flat.json'))}
used = {}
for g in GROUPS:
    for m in g['members']:
        if m in used: print("DUP member", m, used[m], g['id'])
        used[m] = g['id']
dropped = {d[0] for d in DROPPED}
missing = [k for k in F if k not in used and k not in dropped]
print("missing:", missing)
unknown = [m for m in used if m not in F and m not in SEEDS]
print("unknown:", unknown)
# build units
out = []
for g in GROUPS:
    mem = []
    for m in g['members']:
        if m in SEEDS:
            mem.append(dict(fid=m, title="(seeded lead)", where="", claim=SEEDS[m], evidence="(seeded by the user; not yet verified)", severity=""))
        else:
            f = F[m]
            mem.append(dict(fid=m, title=f['title'], where=f"{f['file']}:{f['function']}:{f['line']}", claim=f['scenario'], evidence=f['evidence'], severity=f['severity'], repro_idea=f['repro_idea']))
    gg = dict(g); gg['members'] = mem
    out.append(gg)
json.dump(out, open('groups.json','w'), indent=1)
print(len(out), "groups;", sum(len(g['members']) for g in GROUPS), "member slots;", len(F), "findings")
# markdown
with open('TRIAGE.md','w') as fh:
    fh.write("# Stage 2 triage\n\nGroups are by root cause. queue=fix: fix queue (ranked). report: verified and reported, below the cap. design: report-only (design/API change).\n\n")
    for g in GROUPS:
        fh.write(f"## {g['id']} {g['slug']} [{g['queue']}, {g['sev']}, {g['kind']}]\n{g['title']}\n\n- members: {', '.join(g['members'])}\n- files: {g['files']}\n- fix strategy: {g['fix']}\n- test approach: {g['test']}\n\n")
    fh.write("## Dropped\n")
    for d in DROPPED: fh.write(f"- {d[0]} ({F[d[0]]['title']}): {d[1]}\n")
    fh.write("\n## Duplicates merged\nEvery finding id listed under a group's members; groups with several members are duplicates/same root cause merged.\n")
