import asyncio, shutil, tempfile, time, zendriver
print("zendriver:", zendriver.__file__)
async def main():
    udd = tempfile.mkdtemp(prefix="q10p-")
    b = await zendriver.start(headless=True, user_data_dir=udd)
    try:
        tab = await b.get("data:text/html,<ul><li>Apples</li><li>Pears</li></ul><p id='p1'>Hello needle world</p><button>Sign up!</button>")
        for label, coro in [
            ("tab(text='Hello needle')", lambda: tab(text="Hello needle", timeout=2)),
            ("tab('Hello needle') positional", lambda: tab("Hello needle", timeout=2)),
            ("tab(text='Sign up!')", lambda: tab(text="Sign up!", timeout=2)),
            ("tab(selector='#p1')", lambda: tab(selector="#p1", timeout=2)),
            ("tab(selector='li')", lambda: tab(selector="li", timeout=2)),
            ("tab(selector='ul > li:nth-child(2)')", lambda: tab(selector="ul > li:nth-child(2)", timeout=2)),
            ("wait_for(text='Hello needle')", lambda: tab.wait_for(text="Hello needle", timeout=2)),
        ]:
            t0 = time.monotonic()
            try:
                r = await asyncio.wait_for(coro(), 20)
                print(f"{label}: OK {time.monotonic()-t0:.2f}s -> {r.tag_name} {r.text!r}")
            except Exception as e:
                print(f"{label}: EXC {time.monotonic()-t0:.2f}s -> {type(e).__name__}: {e}")
    finally:
        await b.stop()
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
