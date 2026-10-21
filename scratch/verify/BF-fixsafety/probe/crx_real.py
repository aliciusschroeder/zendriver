import asyncio, os, sys, zendriver as zd
async def main():
    cfg = zd.Config(headless=True)
    cfg.add_extension(sys.argv[1])
    d = str(cfg._extensions[0])
    b = await zd.start(cfg)
    await b.stop()
    print(zd.__file__, "EXTRACTED", d, "exists after stop:", os.path.isdir(d))
asyncio.run(asyncio.wait_for(main(), 60))
