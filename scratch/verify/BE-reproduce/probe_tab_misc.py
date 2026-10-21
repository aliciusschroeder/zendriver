import asyncio, os, sys, json, base64, pathlib, warnings, _pyio, shutil
import zendriver
import zendriver.core.tab as tabmod
from zendriver import cdp
from common import serve
print("zendriver:", zendriver.__file__, "python", sys.version.split()[0])
WORK = pathlib.Path(__file__).parent / "work_misc"
shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir()
os.chdir(WORK)

async def main():
    srv, base = serve()
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        # A7.5 / A12.7
        got = await tab.get_all_urls()
        truth = await tab.evaluate("[...document.querySelectorAll('a,link,img,script,meta')].map(e=>e.href||e.src).filter(Boolean)")
        print("A7.5 page url:", tab.url)
        print("A7.5 get_all_urls():", got)
        print("A7.5 browser-resolved:", truth)

        # A7.6 set_user_agent drops client hints
        b1 = await tab.evaluate("JSON.stringify([navigator.userAgentData.brands, navigator.userAgentData.platform])")
        await tab.set_user_agent(accept_language="de-DE")
        await tab.reload(); await tab.wait_for_ready_state("complete")
        b2 = await tab.evaluate("JSON.stringify([navigator.userAgentData.brands, navigator.userAgentData.platform, navigator.language])")
        print("A7.6 before:", b1)
        print("A7.6 after set_user_agent(accept_language='de-DE'):", b2)

        # A7.9 / B16.18
        try:
            p = await tab.save_screenshot(format="webp")
            print("A7.9 webp saved:", p)
        except Exception as e:
            print("A7.9 save_screenshot(format='webp') raised", type(e).__name__, e)
        # A7.10
        p1 = await tab.save_screenshot()
        p2 = await tab.save_screenshot()
        print("A7.10 p1", p1, "p2", p2, "same:", p1 == p2, "jpgs:", sorted(x for x in os.listdir('.') if x.endswith('.jpg')))
        # A7.12
        p = await tab.print_to_pdf("s.pdf", transfer_mode="ReturnAsStream")
        print("A7.12 ReturnAsStream size:", os.path.getsize(p))
        p = await tab.print_to_pdf("n.pdf")
        print("A7.12 control default size:", os.path.getsize(p))
        # show a stream handle is returned and left open
        data, handle = await tab.send(cdp.page.print_to_pdf(transfer_mode="ReturnAsStream"))
        print("A7.12 raw: data len", len(data), "handle", handle)
        chunk = await tab.send(cdp.io.read(handle, size=8))
        print("A7.12 raw read first chunk:", chunk[:2] if isinstance(chunk, tuple) else chunk)
        await tab.send(cdp.io.close(handle))

        # A7.8 save_snapshot in text mode: emulate Windows text-mode newline translation
        await tab.save_snapshot("ok.mhtml")
        raw = pathlib.Path("ok.mhtml").read_bytes()
        print("A7.8 linux file: CRLF count", raw.count(b"\r\n"), "CRCRLF count", raw.count(b"\r\r\n"))
        orig_linesep = os.linesep
        os.linesep = "\r\n"
        tabmod.open = _pyio.open  # module-global shadow of builtin open, Windows-like newline=None semantics
        try:
            await tab.save_snapshot("win.mhtml")
        finally:
            os.linesep = orig_linesep
            del tabmod.open
        raw = pathlib.Path("win.mhtml").read_bytes()
        print("A7.8 emulated-windows file: CRCRLF count", raw.count(b"\r\r\n"))
        for f in ("ok.mhtml", "win.mhtml"):
            t = await browser.get("file://" + str(WORK / f), new_tab=True)
            await asyncio.sleep(1.5)
            txt = await t.evaluate("document.body ? document.body.innerText : '<no body>'")
            print(f"A7.8 render {f}: {txt!r}")
            await t.close()

        # A7.7 download_file with quote in filename
        await tab.set_download_path(WORK / "dl")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            await tab.download_file(base + "/docs/data.txt", "plain.txt")
            await tab.download_file(base + "/docs/data.txt", "O'Reilly.txt")
            await tab.download_file(base + "/docs/data.txt", "back\\slash.txt")
        await asyncio.sleep(3)
        print("A7.7 files in dl:", sorted(os.listdir(WORK / "dl")))
        code = "(elem) => { _f('%s', '%s'); function _f(a,b){} }" % (base, "O'Reilly.txt")
        body = (await tab.query_selector_all("body"))[0]
        await body.update()
        r = await tab.send(cdp.runtime.call_function_on(code, object_id=body.object_id, arguments=[cdp.runtime.CallArgument(object_id=body.object_id)]))
        print("A7.7 raw call_function_on with quote -> exceptionDetails:", r[1].exception.description if r[1] and r[1].exception else r[1])
        # injection: url containing a quote runs JS
        await tab.evaluate("window.__pwn = 0")
        await tab.download_file(base + "/docs/data.txt'); window.__pwn=1; ('", "inj.txt")
        await asyncio.sleep(1)
        print("A7.7 injection window.__pwn =", await tab.evaluate("window.__pwn"))
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 110))
