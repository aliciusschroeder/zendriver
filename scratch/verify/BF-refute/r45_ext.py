import asyncio, sys, os, pathlib, tempfile, zipfile, shutil, glob, json
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
WORK = pathlib.Path(sys.argv[1])
MAN = {"manifest_version": 3, "name": "bfref", "version": "1.0", "background": {"service_worker": "sw.js"}}
def make_ext(d, nested):
    d.mkdir(parents=True)
    (d/"manifest.json").write_text(json.dumps(MAN)); (d/"sw.js").write_text("self.addEventListener('install',()=>{});")
    if nested:
        (d/"web").mkdir(); (d/"web"/"manifest.webmanifest").write_text("{}")
async def ext_targets(browser):
    await asyncio.sleep(2)
    infos = await browser.connection.send(cdp.target.get_targets())
    return [t.url for t in infos if t.url.startswith("chrome-extension://")]
async def run(label, add):
    cfg = zd.Config(headless=True)
    add(cfg)
    print(label, "config._extensions:", cfg._extensions)
    browser = await zd.start(cfg)
    try:
        print(label, "extension targets:", await ext_targets(browser))
    finally:
        await browser.stop()
    return cfg
async def main():
    make_ext(WORK/"ext_plain", False); make_ext(WORK/"ext_nested", True)
    await run("[dir plain]", lambda c: c.add_extension(WORK/"ext_plain"))
    await run("[dir w/ nested manifest.*]", lambda c: c.add_extension(WORK/"ext_nested"))
    crx = WORK/"ext.crx"
    with zipfile.ZipFile(crx, "w") as z:
        z.writestr("manifest.json", json.dumps(MAN)); z.writestr("sw.js", "")
    before = set(glob.glob(tempfile.gettempdir()+"/extension_*"))
    cfg = await run("[crx]", lambda c: c.add_extension(crx))
    after = set(glob.glob(tempfile.gettempdir()+"/extension_*"))
    new = after - before
    print("[crx] extracted dir still exists after browser.stop():", {d: os.path.isdir(d) for d in new})
    print("[crx] user_data_dir removed:", not os.path.exists(cfg.user_data_dir))
    for d in new: shutil.rmtree(d)
asyncio.run(asyncio.wait_for(main(), 100))
