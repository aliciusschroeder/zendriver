import asyncio, sys
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__)
D = sys.argv[1]
async def run(label, coro):
    try:
        r = await asyncio.wait_for(coro, 15)
        print(f"[{label}] OK ->", repr(r)[:300])
    except Exception as e:
        print(f"[{label}] EXC {type(e).__name__}: {str(e)[:300]}")
async def main():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get(f"file://{D}/page_r33.html")
        await tab.sleep(0.3)
        box = await tab.select('#box')
        await run("apply throw", box.apply('(e) => { throw new Error("boom") }'))
        await run("apply reject", box.apply('async (e) => { throw new Error("boom") }', await_promise=True))
        await run("apply undefined", box.apply('(e) => { }'))
        await run("evaluate throw", tab.evaluate('(() => { throw new Error("boom") })()'))
        r = await box.apply('(e) => e.firstElementChild', return_by_value=False)
        print("[apply rbv False] ->", type(r).__name__, "object_id=", getattr(r, 'object_id', None), "value=", getattr(r,'value',None))
        # raw CDP to show what Chrome returns on throw
        ro = await tab.send(cdp.dom.resolve_node(backend_node_id=box.backend_node_id))
        raw = await tab.send(cdp.runtime.call_function_on('(e) => { throw new Error("boom") }', object_id=ro.object_id, arguments=[cdp.runtime.CallArgument(object_id=ro.object_id)], return_by_value=True))
        print("[raw callFunctionOn throw] result[0]=", repr(raw[0])[:150], "\n   result[1] is None?", raw[1] is None, repr(raw[1])[:150])
        ta = await tab.select('#ta')
        await run("clear_input textarea", ta.clear_input())
        print("   textarea value after:", repr(await tab.evaluate("document.getElementById('ta').value")))
        await run("clear_input_by_deleting textarea", ta.clear_input_by_deleting())
        print("   textarea value after:", repr(await tab.evaluate("document.getElementById('ta').value")))
        inp = await tab.select('#inp')
        await run("clear_input input", inp.clear_input())
        print("   input value after:", repr(await tab.evaluate("document.getElementById('inp').value")))
        circ = await tab.select('#circ')
        await run("get_js_attributes circ", circ.get_js_attributes())
    finally:
        await browser.stop()
asyncio.run(main())
