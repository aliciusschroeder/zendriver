import pathlib
import sys

path = pathlib.Path(sys.argv[1])
src = path.read_text()
old = """            results = await asyncio.wait_for(
                asyncio.gather(
                    *(target.aclose() for target in self.targets),
                    return_exceptions=True,
                ),
                STOP_COMMAND_TIMEOUT,
            )
"""
new = """            async def _detach_all() -> list:
                return await asyncio.gather(
                    *(target.aclose() for target in self.targets),
                    return_exceptions=True,
                )

            results = await asyncio.wait_for(_detach_all(), STOP_COMMAND_TIMEOUT)
"""
assert src.count(old) == 1
path.write_text(src.replace(old, new))
print("patched")
