"""apply one textual mutation to the worktree's connection.py, run the
connection tests, then restore the file content exactly"""

import os
import subprocess
import sys

W = "/home/user/zendriver/.claude/worktrees/wf_2c9e79a3-fb2-5"
S = "/tmp/claude-0/-home-user-zendriver/b2021b39-94e6-5220-9e66-7f33c0314a80/scratchpad/followup/U1-review1"
F = os.path.join(W, "zendriver/core/connection.py")

MUTATIONS = {
    "M1_no_stand_in": (
        "                        self._expect_enable_response(written, domain_mod)\n",
        "                        pass\n",
    ),
    "M2_no_tx_exception": (
        "                    tx.exception()\n",
        "                    pass\n",
    ),
    "M3_no_manual_undo": (
        "                    self.manually_enabled_domains.remove(manual_domain)\n",
        "                    pass\n",
    ),
    "M4_no_done_check": (
        "            if not tx.done():\n                if self.websocket is None:",
        "            if True:\n                if self.websocket is None:",
    ),
    "M5_sentinel_empty": (
        "_ReceiveError(e, list(session.mapper))",
        "_ReceiveError(e, [])",
    ),
    "M6_direct_fail": (
        "                    if session._inbox is not None:\n                        # only after",
        "                    if False:\n                        # only after",
    ),
    "M7_method_match": (
        "if t.__cdp_obj__ is enable",
        "if t.method == domain_mod.__name__ and False or t.method.endswith('.enable')",
    ),
    "M8_no_pop": (
        "                self.mapper.pop(tx.id, None)\n                if tx.done() and not tx.cancelled():",
        "                if tx.done() and not tx.cancelled():",
    ),
    "M9_always_rollback": (
        "                    if written is None:\n",
        "                    if True:\n",
    ),
}


def main() -> None:
    names = sys.argv[1:] or list(MUTATIONS)
    original = open(F).read()
    try:
        for name in names:
            old, new = MUTATIONS[name]
            assert original.count(old) == 1, (name, original.count(old))
            open(F, "w").write(original.replace(old, new))
            for label, env in (("3.10", {}), ("3.13", {"UV_PROJECT_ENVIRONMENT": S + "/venv313"})):
                r = subprocess.run(
                    ["timeout", "300", "uv", "run", "pytest", "tests/core/test_connection.py",
                     "-p", "no:cacheprovider", "-q", "--tb=no", "-x" if False else "-q"],
                    cwd=W, env={**os.environ, **env}, capture_output=True, text=True,
                )
                lines = [l for l in r.stdout.splitlines() if l.startswith("FAILED") or "passed" in l or "failed" in l]
                print(f"--- {name} {label}")
                for l in lines:
                    print("   ", l)
    finally:
        open(F, "w").write(original)


main()
