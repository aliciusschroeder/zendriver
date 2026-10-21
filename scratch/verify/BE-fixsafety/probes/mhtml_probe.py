import asyncio, pathlib, tempfile, shutil
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
async def main():
    d = pathlib.Path(tempfile.mkdtemp())
    (d/"p.html").write_text("<html><body><h1>Hello Login</h1><p>Sign in now</p></body></html>")
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get((d/"p.html").as_uri())
        await tab.wait_for_ready_state("complete")
        data = await tab.send(cdp.page.capture_snapshot())
        (d/"ok.mhtml").write_bytes(data.encode())
        (d/"win.mhtml").write_bytes(data.replace("\r\n", "\r\r\n").encode())  # what text mode writes on windows
        for n in ["ok.mhtml", "win.mhtml"]:
            t = await browser.get((d/n).as_uri())
            await asyncio.sleep(1)
            print(n, repr(await t.evaluate("document.body ? document.body.innerText : null")))
    finally:
        await browser.stop(); shutil.rmtree(d, ignore_errors=True)
asyncio.run(asyncio.wait_for(main(), 60))
