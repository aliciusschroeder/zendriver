import pathlib, sys
p = pathlib.Path(sys.argv[1])
s = p.read_text()
old = """            results = await asyncio.wait_for(
                detach_from_targets(), STOP_COMMAND_TIMEOUT
            )"""
new = """            results = await asyncio.wait_for(
                asyncio.gather(
                    *(target.aclose() for target in self.targets),
                    return_exceptions=True,
                ),
                STOP_COMMAND_TIMEOUT,
            )"""
assert s.count(old) == 1
p.write_text(s.replace(old, new))
print("mutated")
