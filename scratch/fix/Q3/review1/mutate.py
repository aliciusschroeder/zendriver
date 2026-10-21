import pathlib
import sys

path = pathlib.Path(sys.argv[1])
which = sys.argv[2]
src = path.read_text()
muts = {
    "M1": [
        (
            "                STOP_COMMAND_TIMEOUT,\n            )\n        except asyncio.TimeoutError",
            "                None,\n            )\n        except asyncio.TimeoutError",
        )
    ],
    "M2": [
        (
            "self.connection.send(cdp.browser.close()), STOP_COMMAND_TIMEOUT",
            "self.connection.send(cdp.browser.close()), None",
        )
    ],
    "M3": [
        (
            "                    return_exceptions=True,\n",
            "                    return_exceptions=False,\n",
        )
    ],
    "M4": [
        (
            "                    if process.poll() is not None:",
            "                    if self._process.poll() is not None:",
        )
    ],
    "M5": [
        (
            "                    while process.poll() is None:\n                        await asyncio.sleep(0.05)",
            "                    await asyncio.to_thread(process.wait)",
        )
    ],
    "M6": [
        (
            "        await self._stop()\n        # only once stopped, so that a stop() which failed or was cancelled\n        # leaves the atexit cleanup in place\n        asyncio_atexit.unregister(self._atexit_cleanup)\n        util.get_registered_instances().discard(self)\n",
            "        asyncio_atexit.unregister(self._atexit_cleanup)\n        util.get_registered_instances().discard(self)\n        await self._stop()\n",
        )
    ],
}
for old, new in muts[which]:
    assert src.count(old) == 1, (which, old)
    src = src.replace(old, new)
path.write_text(src)
print("applied", which)
