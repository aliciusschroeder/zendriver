import asyncio, os, sys, pathlib, math
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
D = os.path.dirname(os.path.abspath(__file__))
URL = pathlib.Path(D, "r46.html").as_uri()

def pid_alive(pid):
    try:
        os.kill(pid, 0); 
        with open(f"/proc/{pid}/stat") as f: st = f.read().split()[2]
        return st != "Z"
    except OSError:
        return False

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(URL)
        await tab.sleep(0.5)
        # A8.10 save_to_dom
        for sel in ("#cmt", "#esc", "#q"):
            el = await tab.select(sel)
            before = await tab.evaluate(f"document.querySelector('{sel}').outerHTML")
            el.attrs["data-x"] = "1"
            print(f"[A8.10 {sel}] str(el) = {str(el)!r}")
            try:
                await asyncio.wait_for(el.save_to_dom(), 20)
                print(f"   save_to_dom ok")
            except Exception as e:
                print(f"   save_to_dom raised {type(e).__name__}: {str(e).splitlines()[0][:150]}")
            after = await tab.evaluate(f"(document.querySelector('{sel}')||{{}}).outerHTML")
            txt = await tab.evaluate(f"(document.querySelector('{sel}')||{{}}).innerText")
            print(f"   before outerHTML: {before!r}\n   after  outerHTML: {after!r}\n   after innerText: {txt!r}")
        bold = await tab.evaluate("document.querySelectorAll('#esc b').length")
        print("   #esc now contains <b> elements:", bold)

        # A6.9 evaluate unserializable
        for expr in ("1/0", "Math.max()", "NaN", "-0", "2n**64n", "10n", "undefined", "null", "0"):
            v = await tab.evaluate(expr)
            raw, _ = await tab.send(cdp.runtime.evaluate(expression=expr, return_by_value=True))
            print(f"[A6.9] evaluate({expr!r}) -> {v!r}   raw.value={raw.value!r} unserializable_value={raw.unserializable_value!r} type={raw.type_}")
        v = await tab.evaluate("NaN", return_by_value=False)
        print("[A6.9] evaluate('NaN', return_by_value=False) ->", repr(v))

        # A8.17 / A7.11
        inp = await tab.select("#inp")
        for name, obj in (("Element", inp), ("Tab", tab)):
            try:
                print(f"[hash {name}]", hash(obj))
            except TypeError as e:
                print(f"[hash {name}] TypeError: {e}")
        try:
            s = set(browser.tabs); print("[A7.11] set(browser.tabs) ok", len(s))
        except TypeError as e:
            print("[A7.11] set(browser.tabs) TypeError:", e)
        try:
            s = set(await tab.select_all("input, div")); print("[A8.17] set(select_all) ok", len(s))
        except TypeError as e:
            print("[A8.17] set(select_all) TypeError:", e)
        from zendriver.core.connection import Connection
        print("   Connection.__hash__ is", Connection.__hash__, "| Tab.__hash__ is", type(tab).__hash__)

        # A8.13 remote object leak
        first = None; ids = set()
        N = 2000
        for i in range(N):
            await inp.apply("(e) => 1")
            oid = inp._remote_object.object_id
            ids.add(oid)
            if first is None: first = oid
        print(f"[A8.13] {N} apply() calls -> {len(ids)} distinct object ids; first={first}")
        r, exc = await tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first, return_by_value=True))
        print("   first object id still alive after", N, "calls: this.id =", r.value, "exc:", exc)
        # also check get_properties on first handle
        # contrast: explicitly released handle
        await tab.send(cdp.runtime.release_object(first))
        try:
            r, exc = await tab.send(cdp.runtime.call_function_on("function(){return this.id}", object_id=first, return_by_value=True))
            print("   after explicit Runtime.releaseObject:", r, exc)
        except Exception as e:
            print("   after explicit Runtime.releaseObject: raised", type(e).__name__, str(e).splitlines()[0])
        hs = await tab.send(cdp.runtime.get_heap_usage())
        print("   heap usage after:", hs[:2] if isinstance(hs, tuple) else hs)
    finally:
        await browser.stop()
        print("browser stopped (main)")

    # B16.10 async with
    async with await zd.start(headless=True) as b:
        pid = b._process_pid
        print("[B16.10] inside: pid", pid, "stopped?", b.stopped)
    await asyncio.sleep(2)
    print("[B16.10] after async with: stopped?", b.stopped, "pid", b._process_pid, "pid alive:", pid_alive(pid), "connection open:", b.connection is not None and not b.connection.closed)
    await b.stop()
    await asyncio.sleep(1)
    print("[B16.10] after explicit stop: pid alive:", pid_alive(pid))

asyncio.run(asyncio.wait_for(main(), 110))
