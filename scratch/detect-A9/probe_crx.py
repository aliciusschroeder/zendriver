import asyncio, os, zipfile, json
import zendriver as zd

async def main():
    with zipfile.ZipFile("ext.crx", "w") as z:
        z.writestr("manifest.json", json.dumps({"manifest_version": 3, "name": "probe", "version": "1.0"}))
    config = zd.Config(headless=True)
    config.add_extension("ext.crx")
    extracted = config._extensions[0]
    browser = await asyncio.wait_for(zd.start(config), 30)
    await asyncio.wait_for(browser.stop(), 30)
    print("extracted dir", extracted, "still exists after browser.stop():", os.path.isdir(extracted))
asyncio.run(main())
