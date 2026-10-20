import asyncio, sys, threading, http.server, functools, os, json
import zendriver as zd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    class H(handler.func):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def main():
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(base + "/docs/index.html")
        await tab.wait_for_ready_state("complete")
        # 1. __call__ swap
        try:
            el = await asyncio.wait_for(tab(text="Sign in now", timeout=2), 10)
            print("tab(text=) ->", el)
        except Exception as e:
            print("tab(text='Sign in now') raised", type(e).__name__, e)
        try:
            el = await asyncio.wait_for(tab(selector="#b", timeout=2), 10)
            print("tab(selector='#b') ->", el)
        except Exception as e:
            print("tab(selector='#b') raised", type(e).__name__, e)
        el = await tab.wait_for(text="Sign in now", timeout=2)
        print("wait_for(text=) ->", el)
        # 2. hash
        try:
            print("hash(tab)", hash(tab))
        except Exception as e:
            print("hash(tab) raised", type(e).__name__, e)
        # 3. get_all_urls
        print("get_all_urls(absolute=True):")
        for u in await tab.get_all_urls():
            print("   ", u)
        print("get_all_urls(absolute=False):", await tab.get_all_urls(absolute=False))
        print("JS-resolved:", await tab.evaluate("[...document.querySelectorAll('a,link,img,script')].map(e=>e.href||e.src)", return_by_value=True))
        # 4. user agent client hints
        before = await tab.evaluate("JSON.stringify(navigator.userAgentData && navigator.userAgentData.brands)")
        print("brands before:", before)
        await tab.set_user_agent(accept_language="de-DE")
        await tab.reload()
        await tab.wait_for_ready_state("complete")
        after = await tab.evaluate("JSON.stringify(navigator.userAgentData && navigator.userAgentData.brands)")
        print("brands after set_user_agent(accept_language=...):", after)
        print("platform hint after:", await tab.evaluate("navigator.userAgentData && navigator.userAgentData.platform"))
        # 5. save_screenshot webp
        try:
            p = await tab.save_screenshot(format="webp")
            print("save_screenshot(webp) ->", p)
        except Exception as e:
            print("save_screenshot(format='webp') raised", type(e).__name__, e)
    finally:
        await browser.stop()
        srv.shutdown()

asyncio.run(asyncio.wait_for(main(), 90))
