import asyncio, sys, os, glob, json, time, base64, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zendriver as zd
from zendriver import cdp
from helpers import serve
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
WORK = os.path.join(HERE, "work")

async def main():
    httpd, base = serve()
    browser = await zd.start(headless=True)
    os.chdir(WORK)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        # A7.5 / A12.7
        got = await tab.get_all_urls()
        truth = await tab.evaluate("JSON.stringify([...document.querySelectorAll('a,link,img,script,meta')].map(e=>e.href||e.src).filter(Boolean))")
        print("A7.5 get_all_urls():", got)
        print("A7.5 browser    :", json.loads(truth))
        # A7.6
        b0 = await tab.evaluate("JSON.stringify([navigator.userAgentData.brands, navigator.userAgentData.platform, navigator.userAgent])")
        await tab.set_user_agent(accept_language="de-DE")
        await tab.reload(); await tab.wait_for_ready_state("complete")
        b1 = await tab.evaluate("JSON.stringify([navigator.userAgentData.brands, navigator.userAgentData.platform, navigator.userAgent, navigator.language])")
        print("A7.6 before:", b0)
        print("A7.6 after :", b1)
        # A7.9 / B16.18
        try:
            p = await tab.save_screenshot(format="webp")
            print("A7.9 webp ok", p)
        except Exception as e:
            print("A7.9 webp EXC", type(e).__name__, e)
        # A7.10
        p1 = await tab.save_screenshot(); p2 = await tab.save_screenshot()
        print("A7.10 p1", p1, "p2", p2, "same", p1 == p2, "jpgs", glob.glob("*.jpg"))
        # A7.12
        try:
            p = await tab.print_to_pdf(os.path.join(WORK, "s.pdf"), transfer_mode="ReturnAsStream")
            print("A7.12 stream size", os.path.getsize(p))
        except Exception as e:
            print("A7.12 EXC", type(e).__name__, e)
        p = await tab.print_to_pdf(os.path.join(WORK, "n.pdf"))
        print("A7.12 control size", os.path.getsize(p))
        # A7.8 snapshot content
        await tab.save_snapshot(os.path.join(WORK, "page.mhtml"))
        raw = open(os.path.join(WORK, "page.mhtml"), "rb").read()
        print("A7.8 CRLF count", raw.count(b"\r\n"), "bare LF", raw.count(b"\n") - raw.count(b"\r\n"), "ascii", all(c < 128 for c in raw))
        win = raw.replace(b"\r\n", b"\r\r\n")  # what newline=None text mode does on Windows (\n -> \r\n)
        open(os.path.join(WORK, "win.mhtml"), "wb").write(win)
        for name in ["page.mhtml", "win.mhtml"]:
            t2 = await browser.get("file://" + os.path.join(WORK, name), new_tab=True)
            await asyncio.sleep(1.5)
            txt = await t2.evaluate("document.body ? document.body.innerText : '<nobody>'")
            print("A7.8", name, "->", repr(txt)[:80])
            await t2.close()
        # A7.7 download_file with quote
        dl = os.path.join(HERE, "dl", "a77")
        os.makedirs(dl, exist_ok=True)
        await tab.set_download_path(dl)
        await tab.download_file(base + "/docs/data.txt", "plain.txt")
        await tab.download_file(base + "/docs/data.txt", "O'Reilly.txt")
        await asyncio.sleep(2.5)
        print("A7.7 files:", sorted(os.listdir(dl)))
        # show swallowed exceptionDetails
        body = (await tab.query_selector_all("body"))[0]; await body.update()
        r = await tab.send(cdp.runtime.call_function_on("(e)=>{ _f('x', 'O'Reilly') }", object_id=body.object_id))
        print("A7.7 callFunctionOn returns (no raise):", type(r[1]).__name__ if r[1] else None, r[1].exception.description if r[1] and r[1].exception else "")
    finally:
        await browser.stop()
        httpd.shutdown()

asyncio.run(asyncio.wait_for(main(), 100))
