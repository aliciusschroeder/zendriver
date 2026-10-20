export const meta = {
  name: 'zendriver-verify',
  description: 'Stage 3: per group (or bundle of small groups), 3 independent verifiers (reproduce, refute/realism, fix-safety) try to disprove each root-cause group; a group survives with >=2 confirms',
  phases: [
    { title: 'Verify fix queue', detail: 'Q1-Q12, one pipeline per group' },
    { title: 'Verify candidates', detail: 'R13-R24 promotion candidates and seeded leads' },
    { title: 'Verify bundles', detail: 'small report-only groups, bundled 4 per pipeline' },
  ],
}

const SCR = '/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad'
const GDIR = `${SCR}/triage/groups`

const SINGLE_Q = ['Q1','Q2','Q3','Q4','Q5','Q6','Q7','Q8','Q9','Q10','Q11','Q12']
const SINGLE_R = ['R13','R14','R15','R16','R18','R19','R20','R21','R22','R23','R24']
const BUNDLES = [
  { id: 'BA', groups: ['R17','R25','R35','R41'] },
  { id: 'BB', groups: ['R26','R27','R30','R42'] },
  { id: 'BC', groups: ['R28','R29','R36','R37'] },
  { id: 'BD', groups: ['R32','R33','R34','R46'] },
  { id: 'BE', groups: ['R38','R39','R40','R31'] },
  { id: 'BF', groups: ['R43','R44','R45','R47'] },
]

const UNITS = [
  ...SINGLE_Q.map(g => ({ id: g, groups: [g], phase: 'Verify fix queue' })),
  ...SINGLE_R.map(g => ({ id: g, groups: [g], phase: 'Verify candidates' })),
  ...BUNDLES.map(b => ({ id: b.id, groups: b.groups, phase: 'Verify bundles' })),
]

const COMMON = `You are an independent VERIFIER in a bug hunt of zendriver, an async Chrome DevTools Protocol (CDP) browser automation library for Python >= 3.10 (repo checked out read-only at /home/user/zendriver, branch ccr-9a8a26e1-b0l7bh). Your job is to try to DISPROVE a root-cause group of reported bugs. Other verifiers with different lenses work on the same group independently; you will not see their results.

GROUND RULES
- Read the code FRESH. Never trust the line numbers, scripts, or evidence in the group file: they are unverified claims from earlier finders. Do not run or copy their probe scripts; write your own.
- NEVER modify anything under /home/user/zendriver (no edits, no git commands that change state, no uv sync, no uv add). Read-only commands (grep, git log -S, git blame, git show) are fine.
- Work ONLY in your scratch dir (given below). Make it with mkdir -p.
- Out of scope: zendriver/cdp/ (generated code; you may read it), docs/, examples/, CI config. Tab.get/Browser.get timeouts that cover only part of the method are owned by another PR (not your concern).
- Default to refuted/not-reproduced when you cannot demonstrate the problem. A claim you only reasoned about is weaker than one you ran.
- Clean up after yourself: stop every browser you start (await browser.stop(), or kill only the pids YOU started) and remove temp dirs you created. Never kill processes you did not start.

ENVIRONMENT
- Python: /home/user/zendriver/.venv/bin/python (Python 3.13, websockets 14.1; zendriver is installed editable from the repo). /usr/bin/python3.11 and /usr/bin/python3.12 exist if a claim is Python-version dependent (you can make a throwaway venv in your scratch dir with uv venv -p 3.11 and uv pip install the repo's deps + PYTHONPATH, only if it matters).
- Real headless Chromium: export PATH=${SCR}/bin:$PATH (a 'chromium' symlink lives there); e.g. browser = await zendriver.start(headless=True). The container runs as root, so is_root() turns the sandbox off and adds --no-sandbox.
- Fake CDP peer: an in-process websockets server (websockets.serve / websockets.asyncio.server.serve) on 127.0.0.1:0 that can answer, drop or delay replies by method name and flood events, then Connection(ws_url) against it.
- For hangs: print the stuck task's stack (task.print_stack()) to show where it is stuck. Always use an OUTER safety net that does not depend on the code under test: run scripts under \`timeout 120 ...\` and use asyncio.wait_for with a POSITIVE timeout around the call.

GOTCHAS (important)
- To test a scratch copy: mkdir -p <dir>/pkg && cp -r /home/user/zendriver/zendriver <dir>/pkg/ ; then set PYTHONPATH=<dir>/pkg, run from a cwd OUTSIDE the repo with \`--rootdir <dir> -p no:cacheprovider -o asyncio_mode=auto\`, and print zendriver.__file__ in the test/probe to prove which copy was imported. tests/ in the repo has an __init__.py, so pytest's rootdir insertion would otherwise import the repo copy. Put your test files in your scratch dir, not in the repo.
- Connection uses the CantTouchThis metaclass, so its class attributes can't be monkeypatched. Patch instances, Listener or \`websockets.connect\`, or use a fake server.
- The container runs as root: is_root() turns the sandbox off and adds --no-sandbox; monkeypatch zendriver.core.config.is_root to test sandbox=True.
- asyncio.wait_for(x, 0) cancels x before its first step. Never use timeout=0 to test a hang path; use a positive timeout plus an outer safety net.
- Line numbers drift; always cite the function name with the line.
- On Python >= 3.12 asyncio.wait_for no longer wraps the awaitable in a new task and websockets returns buffered frames without suspending, so some ordering races only show up on 3.12+; say which Python you ran when it matters.`

const LENSES = {
  reproduce: `YOUR LENS: REPRODUCE. Build your OWN reproducer for each member claim (prioritise the group's root cause and its most severe members; for a bundle, cover every group). For runtime bugs use a fake CDP peer or the real headless Chromium. For hangs, print the task's stack to show where it is stuck, under an outer safety net. Record the exact command(s) you ran and the key output lines. A member is "confirmed" only if your own run shows the wrong result / hang / leak / crash; "not-reproduced" if your honest attempt did not show it; "refuted" if you showed it cannot happen.`,
  refute: `YOUR LENS: REFUTE / REALISM. Argue that the bug can't be reached or doesn't matter, and only concede when you can't. Look for: calls already serialised upstream; bounds from keepalive (websockets ping_timeout etc.), timeouts or close paths that end the wait anyway; callers that never pass the triggering input; intent in git history (git log -S '<snippet>', git blame, git show) showing the behaviour is deliberate; tests asserting the current behaviour. Label EACH statement about Chrome's behaviour as "verified" (you checked it with the real headless browser) or "assumed"; whenever the bug's reality depends on a Chrome behaviour, verify it with the real headless browser. Rate realism: how likely is a normal user to hit this? Give refinements, e.g. "only hangs if the handshakes finish in the same event-loop turn".`,
  fixsafety: `YOUR LENS: FIX-SAFETY. For each group: prototype the MINIMAL fix on a scratch copy (mkdir -p <dir>/pkg && cp -r /home/user/zendriver/zendriver <dir>/pkg/), matching the surrounding style. Write a regression test (pytest, async, prefer browser-free with a fake peer/fake websocket/instance patches; real Chromium only if the bug only shows with Chrome) in your scratch dir, and show it FAILS on the repo code (no PYTHONPATH, imports /home/user/zendriver/zendriver) and PASSES on the prototype (PYTHONPATH=<dir>/pkg) — print zendriver.__file__ in both runs and paste the pass/fail summary lines. Then check: re-entrancy (asyncio.Lock is not reentrant), deadlocks and lock ordering, error/cancel paths, behaviour changes callers would notice, and mypy on the prototype: cd /home/user/zendriver && uv run mypy --config-file pyproject.toml <dir>/pkg/zendriver (report only NEW errors vs the same command on an untouched copy). If the right fix is a design/API change rather than a minimal local patch, say so (kind=design-api) and describe the smallest safe change; you may skip the prototype then. If your test cannot be made to fail on the repo code, that is evidence AGAINST the bug: say so.`,
}

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          group_id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partially-confirmed', 'refuted', 'inconclusive'] },
          summary: { type: 'string' },
          member_verdicts: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                fid: { type: 'string' },
                verdict: { type: 'string', enum: ['confirmed', 'refuted', 'not-reproduced', 'not-checked'] },
                note: { type: 'string' },
              },
              required: ['fid', 'verdict', 'note'],
            },
          },
          evidence: { type: 'string' },
          refinements: { type: 'string' },
          chrome_claims: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                claim: { type: 'string' },
                status: { type: 'string', enum: ['verified', 'assumed'] },
                how: { type: 'string' },
              },
              required: ['claim', 'status', 'how'],
            },
          },
          realism: { type: 'string', enum: ['high', 'medium', 'low'] },
          severity: { type: 'string', enum: ['crash', 'hang', 'leak', 'wrong-result', 'cosmetic'] },
          fix_assessment: {
            type: 'object',
            properties: {
              kind: { type: 'string', enum: ['minimal-local', 'design-api', 'none-needed', 'not-assessed'] },
              prototype_dir: { type: 'string' },
              diff_summary: { type: 'string' },
              regression_test_path: { type: 'string' },
              fails_on_repo: { type: 'string', enum: ['yes', 'no', 'not-run'] },
              passes_on_prototype: { type: 'string', enum: ['yes', 'no', 'not-run'] },
              mypy_ok: { type: 'string', enum: ['yes', 'no', 'not-run'] },
              risks: { type: 'string' },
            },
            required: ['kind', 'prototype_dir', 'diff_summary', 'regression_test_path', 'fails_on_repo', 'passes_on_prototype', 'mypy_ok', 'risks'],
          },
        },
        required: ['group_id', 'verdict', 'summary', 'member_verdicts', 'evidence', 'refinements', 'chrome_claims', 'realism', 'severity', 'fix_assessment'],
      },
    },
  },
  required: ['groups'],
}

function prompt(unit, lens) {
  const dir = `${SCR}/verify/${unit.id}-${lens}`
  const files = unit.groups.map(g => `${GDIR}/${g}.md`).join('\n')
  const bundleNote = unit.groups.length > 1
    ? `\nThis is a BUNDLE of ${unit.groups.length} small, independent groups (${unit.groups.join(', ')}). Verify EACH group and return one entry per group in "groups". Budget your effort across all of them; check every member at least by code reading, and run something for the most severe members of each group.`
    : ''
  return `${COMMON}\n\n${LENSES[lens]}\n\nYOUR SCRATCH DIR: ${dir}/\n\nGROUP DEFINITION FILE(S) — read them first:\n${files}\n${bundleNote}\nReturn one "groups" entry per group id (${unit.groups.join(', ')}), with a per-member verdict for every member listed in the file. For lenses other than fix-safety, set fix_assessment.kind to your best judgement (or not-assessed) and the other fix fields to "" / "not-run".`
}

const LENS_KEYS = ['reproduce', 'refute', 'fixsafety']

const results = await pipeline(
  UNITS,
  unit => parallel(LENS_KEYS.map(lens => () =>
    agent(prompt(unit, lens), {
      label: `${unit.id}:${lens}`,
      phase: unit.phase,
      schema: RESULT_SCHEMA,
    }).then(r => ({ lens, result: r }))
  )),
  (lensResults, unit) => {
    const out = []
    for (const gid of unit.groups) {
      const votes = []
      for (const lr of (lensResults || []).filter(Boolean)) {
        const g = lr.result && lr.result.groups ? lr.result.groups.find(x => x.group_id === gid) : null
        votes.push({ lens: lr.lens, verdict: g ? g.verdict : 'missing', entry: g })
      }
      const confirms = votes.filter(v => v.verdict === 'confirmed' || v.verdict === 'partially-confirmed').length
      // per-member tally
      const memberTally = {}
      for (const v of votes) {
        if (!v.entry) continue
        for (const m of v.entry.member_verdicts || []) {
          memberTally[m.fid] = memberTally[m.fid] || { confirmed: 0, refuted: 0, other: 0 }
          if (m.verdict === 'confirmed') memberTally[m.fid].confirmed++
          else if (m.verdict === 'refuted') memberTally[m.fid].refuted++
          else memberTally[m.fid].other++
        }
      }
      out.push({ group_id: gid, unit: unit.id, confirms, survives: confirms >= 2, votes: votes.map(v => ({ lens: v.lens, verdict: v.verdict })), memberTally, lenses: votes.map(v => ({ lens: v.lens, entry: v.entry })) })
    }
    log(`${unit.id}: ` + out.map(o => `${o.group_id} ${o.survives ? 'SURVIVES' : 'dropped'} (${o.votes.map(v => v.verdict[0]).join('')})`).join('; '))
    return out
  },
)

return { groups: results.filter(Boolean).flat() }
