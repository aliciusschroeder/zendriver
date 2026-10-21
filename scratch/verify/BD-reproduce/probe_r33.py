import asyncio, os, sys, pathlib
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, "python", sys.version.split()[0])
D = os.path.dirname(os.path.abspath(__file__))
URL = pathlib.Path(D, "r33.html").as_uri()

async def run(label, coro):
    try:
        r = await asyncio.wait_for(coro, 20)
        print(f"[{label}] returned {r!r}"[:400])
        return r
    except Exception as e:
        print(f"[{label}] raised {type(e).__name__}: {str(e)[:250]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(URL)
        await tab.sleep(0.5)
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); ta2 = await tab.select("#ta2")
        # A8.6 / B15.8
        await run("apply throw", inp.apply('(e) => { throw new Error("boom") }'))
        await run("apply undefined", inp.apply('(e) => { }'))
        await run("apply async reject await_promise", inp.apply('async (e) => { throw new Error("boom") }', await_promise=True))
        await run("apply throw rbv=False", inp.apply('(e) => { throw new Error("boom") }', return_by_value=False))
        # raw CDP to show exceptionDetails was there
        ro = await tab.send(cdp.dom.resolve_node(backend_node_id=inp.backend_node_id))
        raw = await tab.send(cdp.runtime.call_function_on('(e) => { throw new Error("boom") }', object_id=ro.object_id,
              arguments=[cdp.runtime.CallArgument(object_id=ro.object_id)], return_by_value=True))
        print("[raw callFunctionOn] result[0]=", repr(raw[0])[:200], "\n   result[1] is None?", raw[1] is None, "text:", raw[1].text if raw[1] else None, "exc desc:", raw[1].exception.description[:40] if raw[1] and raw[1].exception else None)
        await run("tab.evaluate throw (contrast)", tab.evaluate('(() => { throw new Error("boom") })()'))
        circ = await tab.select("#circ")
        await run("get_js_attributes circ", circ.get_js_attributes())
        # A8.7
        r = await run("apply parentElement rbv=False", inp.apply('(e) => e.parentElement', return_by_value=False))
        if r is not None:
            print("   object_id:", getattr(r, "object_id", "n/a"), "type:", getattr(r, "type_", None), "value:", getattr(r, "value", None))
        # A8.5
        await run("clear_input input", inp.clear_input())
        print("   input value now:", repr(await tab.evaluate("document.getElementById('inp').value")))
        await run("clear_input textarea", ta.clear_input())
        print("   textarea value now:", repr(await tab.evaluate("document.getElementById('ta').value")))
        await run("clear_input_by_deleting textarea", ta2.clear_input_by_deleting())
        print("   textarea2 value now:", repr(await tab.evaluate("document.getElementById('ta2').value")))
        # pre-b506c8f behaviour for contrast
        await run("old impl element.value='' on textarea", ta.apply('function (element) { element.value = "" } '))
        print("   textarea value now:", repr(await tab.evaluate("document.getElementById('ta').value")))
        # what exception does the setter throw?
        print("   setter on textarea in page:", await tab.evaluate("(()=>{try{Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(document.getElementById('ta2'),'');return 'ok'}catch(e){return String(e)}})()"))
    finally:
        await browser.stop()
        print("browser stopped")

asyncio.run(asyncio.wait_for(main(), 110))
