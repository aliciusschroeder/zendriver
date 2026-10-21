import asyncio, json, pathlib, shutil, sys, tempfile
import zendriver as zd
print("zendriver from", zd.__file__)
D = pathlib.Path(sys.argv[1])

async def main():
    work = pathlib.Path(tempfile.mkdtemp(prefix="smoke_", dir=D))
    ext = work / "headless-language-ext"
    ext.mkdir()
    (ext / "manifest.json").write_text(json.dumps({
        "manifest_version": 3, "name": "r15", "version": "1.0",
        "background": {"service_worker": "sw.js"}}))
    (ext / "sw.js").write_text("self.addEventListener('install', () => {});")
    cfg = zd.Config(headless=True, user_data_dir=work / "profile",
                    browser_args=["--headless=new", "--no-sandbox", "--mute-audio"])
    cfg.add_extension(ext)
    browser = None
    try:
        browser = await asyncio.wait_for(zd.start(cfg), 60)
        cmd = pathlib.Path(f"/proc/{browser._process_pid}/cmdline").read_bytes().split(b"\0")
        cmd = [c.decode() for c in cmd if c]
        print("load-extension flags:", [c for c in cmd if c.startswith("--load-extension")])
        print("dupes:", sorted({c for c in cmd if cmd.count(c) > 1}))
        await asyncio.sleep(2)
        from zendriver import cdp
        infos = await browser.connection.send(cdp.target.get_targets())
        print("extension targets:", [(t.type_, t.url[:40]) for t in infos if t.url.startswith("chrome-extension://")])
    except Exception as e:
        print("START FAILED:", type(e).__name__, str(e)[:120])
    finally:
        if browser is not None:
            await browser.stop()
        shutil.rmtree(work, ignore_errors=True)

asyncio.run(main())
