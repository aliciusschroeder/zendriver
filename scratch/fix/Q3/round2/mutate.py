"""applies one mutation to zendriver/core/browser.py in the given worktree"""

import pathlib
import sys

worktree, mutation = sys.argv[1], sys.argv[2]
path = pathlib.Path(worktree) / "zendriver/core/browser.py"
source = path.read_text()

FORWARDERS = """        # only once the browser is gone, and bounded, because on python >= 3.12.1
        # closing a forwarder waits until the browser's connections to it are
        # closed, which a browser which stopped reading from them holds open
        for forwarder in self._proxy_forwarders:
            try:
                await asyncio.wait_for(forwarder.close(), STOP_COMMAND_TIMEOUT)
            except asyncio.TimeoutError:
                logger.debug("timed out closing a proxy forwarder")
        self._proxy_forwarders.clear()

"""
PROCESS = "        # a concurrent stop() may set self._process to None while this one waits\n"

if mutation == "unbounded_forwarders":
    old = "await asyncio.wait_for(forwarder.close(), STOP_COMMAND_TIMEOUT)"
    new = "await forwarder.close()"
elif mutation == "forwarders_before_process":
    assert source.count(FORWARDERS) == 1
    source = source.replace(FORWARDERS, "")
    old, new = PROCESS, FORWARDERS + PROCESS
elif mutation == "gather_to_wait_for":
    old = "detach_from_targets(), STOP_COMMAND_TIMEOUT"
    new = (
        "asyncio.gather(*(target.aclose() for target in self.targets),"
        " return_exceptions=True), STOP_COMMAND_TIMEOUT"
    )
elif mutation == "unguarded_process_reset":
    old = "            if self._process is process:\n"
    new = "            if True:\n"
else:
    raise SystemExit(f"unknown mutation {mutation}")

assert source.count(old) == 1, mutation
path.write_text(source.replace(old, new))
print("applied", mutation)
