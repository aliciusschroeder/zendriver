import asyncio
import sys
import tempfile

import zendriver as zd
from zendriver.core.connection import Connection


async def main(which: str) -> None:
    if which == "browser":
        cm: object = zd.Browser(
            zd.Config(
                browser_executable_path="/path/to/browser",
                user_data_dir=tempfile.mkdtemp(),
            )
        )
    else:
        cm = Connection("ws://fake/devtools/browser/fake")
    async with cm:  # type: ignore[attr-defined]
        sys.exit(3)


asyncio.run(main(sys.argv[1]))
