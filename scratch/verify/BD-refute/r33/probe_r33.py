import asyncio, sys, pathlib
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
HERE = pathlib.Path(__file__).parent

async def run(label, coro, t=20):
    try:
        r = await asyncio.wait_for(coro, t)
        print(f"[{label}] OK -> {r!r}"[:400])
        return r
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:250]}")

async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get((HERE / "page.html").as_uri())
        await tab.sleep(0.3)
        inp = await tab.select("#inp"); ta = await tab.select("#ta"); circ = await tab.select("#circ")
        await run("apply throw", inp.apply('(e) => { throw new Error("boom") }'))
        await run("apply undefined", inp.apply('(e) => { }'))
        await run("apply reject await", inp.apply('async (e) => { throw new Error("boom") }', await_promise=True))
        await run("apply throw rbv=False", inp.apply('(e) => { throw new Error("boom") }', return_by_value=False))
        await run("apply syntax error", inp.apply('(e) => { ( }'))
        # raw: what does Chrome return?
        ro = await tab.send(cdp.dom.resolve_node(backend_node_id=inp.backend_node_id))
        raw = await tab.send(cdp.runtime.call_function_on('(e) => { throw new Error("boom") }', object_id=ro.object_id, arguments=[cdp.runtime.CallArgument(object_id=ro.object_id)], return_by_value=True))
        print("raw throw result[0]:", raw[0]); print("raw exception details text:", raw[1] and raw[1].text, raw[1] and raw[1].exception and raw[1].exception.description[:40])
        await run("evaluate throw", tab.evaluate('(() => { throw new Error("boom") })()'))
        r = await run("apply parentElement rbv=False", inp.apply('(e) => e.parentElement', return_by_value=False))
        if r is not None: print("   object_id:", getattr(r, "object_id", None))
        r = await run("apply returns 5 rbv=False", inp.apply('(e) => 5', return_by_value=False))
        await run("get_js_attributes circ", circ.get_js_attributes())
        await run("get_js_attributes inp", inp.get_js_attributes(), 30)
        # textarea clear
        await run("clear_input textarea", ta.clear_input())
        print("   ta.value =", await tab.evaluate("document.getElementById('ta').value"), "input events", await tab.evaluate("window.__inputs"))
        await run("clear_input_by_deleting textarea", ta.clear_input_by_deleting())
        print("   ta.value =", await tab.evaluate("document.getElementById('ta').value"))
        await run("clear_input input", inp.clear_input())
        print("   inp.value =", await tab.evaluate("document.getElementById('inp').value"))
        await tab.evaluate("document.getElementById('inp').value='abc'")
        await run("clear_input_by_deleting input", inp.clear_input_by_deleting())
        print("   inp.value =", await tab.evaluate("document.getElementById('inp').value"))
        # direct confirm illegal invocation
        await run("evaluate setter on textarea", tab.evaluate("Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(document.getElementById('ta'),'')"))
        # workaround a user would try: send_keys after clear -> text appended
        await ta.send_keys("NEW")
        print("   after send_keys NEW ta.value =", await tab.evaluate("document.getElementById('ta').value"))
    finally:
        await browser.stop()

asyncio.run(main())
