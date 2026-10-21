"""apply a mutation of the Q12 fix to the worktree's connection.py (reverted with git checkout afterwards)"""

import sys
from pathlib import Path

path = Path(
    "/home/user/zendriver/.claude/worktrees/wf_453a9023-a6b-24/zendriver/core/connection.py"
)
src = path.read_text()
fixed = """                except asyncio.CancelledError:
                    # the enable may not have reached the browser, so don't keep
                    # the domain marked as enabled, and let the cancellation through
                    if domain_mod in self.enabled_domains:
                        self.enabled_domains.remove(domain_mod)
                    raise
"""
assert fixed in src
variant = sys.argv[1]
if variant == "naive":
    # except Exception only, no CancelledError branch
    new = ""
elif variant == "noremove":
    new = """                except asyncio.CancelledError:
                    raise
"""
else:
    raise SystemExit(f"unknown variant {variant}")
path.write_text(src.replace(fixed, new))
print("applied", variant)
