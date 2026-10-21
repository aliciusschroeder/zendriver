import asyncio, sys, os, json, zipfile, tempfile, pathlib, glob
import zendriver
from zendriver import cdp
from zendriver.core import util
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0], "tempdir", tempfile.gettempdir())
HERE = pathlib.Path(sys.path[0])

def make_ext(root: pathlib.Path, nested: bool):
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "manifest_version": 3, "name": "probe-ext", "version": "1.0",
        "background": {"service_worker": "bg.js"}}))
    (root / "bg.js").write_text("self.addEventListener('install', () => {});")
    if nested:
        (root / "web").mkdir(exist_ok=True)
        (root / "web" / "manifest.webmanifest").write_text("{}")
    return root

async def ext_targets(browser):
    await asyncio.sleep(3)
    infos = await browser.connection.send(cdp.target.get_targets())
    return [i.url for i in infos if i.url.startswith("chrome-extension://")]

async def main():
    # A9.9 html_from_tree
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p>hello</p>")
        await asyncio.sleep(0.5)
        doc = await tab.send(cdp.dom.get_document(-1, True))
        h = await util.html_from_tree(doc, tab)
        print("A9.9 html_from_tree(doc):", repr(h))
        print("A9.9 tab.get_content()   :", repr(await tab.get_content()))
        print("A9.9 'hello' count:", h.count("hello"))
    finally:
        await browser.stop()

    # A9.7 add_extension(dir) with nested manifest.*
    for nested in (False, True):
        root = make_ext(HERE / f"ext_nested_{nested}", nested)
        cfg = zendriver.Config(headless=True)
        cfg.add_extension(root)
        print(f"A9.7 nested={nested}: root={root.name} -> _extensions={[str(p).replace(str(HERE)+'/', '') for p in cfg._extensions]}")
        browser = await zendriver.start(cfg)
        try:
            print(f"A9.7 nested={nested}: extension targets after start: {await ext_targets(browser)}")
        finally:
            await browser.stop()

    # A9.11 / B16.17 add_extension(.crx) leaks its extraction dir
    src = make_ext(HERE / "crx_src", False)
    crx = HERE / "ext.crx"
    with zipfile.ZipFile(crx, "w") as z:
        for f in ("manifest.json", "bg.js"):
            z.write(src / f, f)
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), "extension_*")))
    cfg = zendriver.Config(headless=True)
    cfg.add_extension(crx)
    extracted = cfg._extensions[0]
    browser = await zendriver.start(cfg)
    try:
        print("A9.11 crx extension targets:", await ext_targets(browser))
    finally:
        await browser.stop()
    await asyncio.sleep(1)
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), "extension_*")))
    print("A9.11 extracted dir", extracted, "exists after browser.stop():", os.path.isdir(extracted), os.listdir(extracted) if os.path.isdir(extracted) else None)
    print("A9.11 new extension_* dirs left in tempdir:", sorted(after - before))

asyncio.run(asyncio.wait_for(main(), 100))
