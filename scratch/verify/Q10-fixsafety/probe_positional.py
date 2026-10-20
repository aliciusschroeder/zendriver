import asyncio, shutil, tempfile, time, zendriver
print("zendriver:", zendriver.__file__)
async def main():
    udd = tempfile.mkdtemp(prefix="q10p-")
    b = await zendriver.start(headless=True, user_data_dir=udd)
    try:
        tab = await b.get("data:text/html,<p>a cat sat on a button</p><a href='/x'>link</a><button class='go'>Go</button>")
        for arg in ["a", "button", "button.go", "div.nope"]:
            t0 = time.monotonic()
            try:
                r = await asyncio.wait_for(tab(arg, timeout=1), 20)
                print(f"tab({arg!r}) positional: OK {time.monotonic()-t0:.2f}s -> <{r.tag_name}> {r.text!r}")
            except Exception as e:
                print(f"tab({arg!r}) positional: EXC {time.monotonic()-t0:.2f}s -> {type(e).__name__}")
    finally:
        await b.stop()
        shutil.rmtree(udd, ignore_errors=True)
asyncio.run(main())
