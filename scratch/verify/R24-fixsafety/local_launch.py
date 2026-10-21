import asyncio, sys
import zendriver as zd
print("zendriver from", zd.__file__)
async def main():
    b = await asyncio.wait_for(zd.start(headless=True), 60)
    try:
        print("exe:", b.config.browser_executable_path, "pid:", b._process_pid)
        t = await asyncio.wait_for(b.get("data:text/html,<title>ok</title>"), 30)
        print("title:", await t.evaluate("document.title"))
    finally:
        await asyncio.wait_for(b.stop(), 30)
    # missing browser path for a local launch still gives the clear error
    try:
        await zd.start(headless=True, browser_executable_path="/does/not/exist")
    except FileNotFoundError as e:
        print("bogus path -> FileNotFoundError (as before):", str(e).strip().splitlines()[1].strip())
asyncio.run(main())
