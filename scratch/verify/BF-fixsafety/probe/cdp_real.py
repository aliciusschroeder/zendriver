import asyncio, zendriver as zd
from zendriver import cdp
async def main():
    print("zendriver from", zd.__file__)
    b = await zd.start(headless=True)
    try:
        tab = await b.get("data:text/html,<p id=b>x</p>")
        for label, flt in [("typed", cdp.target.TargetFilter([cdp.target.FilterEntry(type_="page")])), ("dict", cdp.target.TargetFilter([{"type": "page"}]))]:
            try:
                infos = await asyncio.wait_for(b.connection.send(cdp.target.get_targets(filter_=flt)), 10)
                print("A13.1", label, "OK", sorted({i.type_ for i in infos}))
            except Exception as e:
                print("A13.1", label, "ERR", type(e).__name__, e)
        body = await tab.select("body")
        ro = await tab.send(cdp.dom.resolve_node(backend_node_id=body.backend_node_id))
        fn = 'function(x){return arguments.length+":"+(x===null?"null":typeof x)}'
        for label, arg in [("None", cdp.runtime.CallArgument(value=None)), ("0", cdp.runtime.CallArgument(value=0)), ("unserializable null", cdp.runtime.CallArgument(unserializable_value=cdp.runtime.UnserializableValue("null")))]:
            r, exc = await tab.send(cdp.runtime.call_function_on(fn, object_id=ro.object_id, arguments=[arg], return_by_value=True))
            print("A13.4", label, "->", r.value, exc)
        el = await tab.select("#b")
        print("A13.3 str(backend_node_id) =", str(el.backend_node_id), "| f'' =", f"{el.backend_node_id}")
    finally:
        await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
