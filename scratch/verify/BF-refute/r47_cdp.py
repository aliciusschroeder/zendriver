import asyncio, sys, json
import zendriver as zd
from zendriver import cdp
print("zendriver from", zd.__file__, sys.version.split()[0])
from zendriver.cdp.target import TargetFilter, FilterEntry
from zendriver.cdp.dom_snapshot import ArrayOfStrings, StringIndex
print("A13.1 offline: TargetFilter.from_json elem type:", type(TargetFilter.from_json([{"type": "page"}])[0]).__name__,
      "| ArrayOfStrings elem is StringIndex:", isinstance(ArrayOfStrings.from_json([1])[0], StringIndex))
print("A13.3 offline: str(NodeId(5))=%r f'{BackendNodeId(6)}'=%r '%%s'%%MonotonicTime(1.5)=%r str(FrameId('abc'))=%r json.dumps=%r" % (
    str(cdp.dom.NodeId(5)), f"{cdp.dom.BackendNodeId(6)}", "%s" % cdp.network.MonotonicTime(1.5), str(cdp.page.FrameId("abc")), json.dumps({"n": cdp.dom.NodeId(5)})))
print("A13.3 offline: int(str(NodeId(5))) ->", end=" ")
try: print(int(str(cdp.dom.NodeId(5))))
except Exception as e: print(type(e).__name__, e)
print("A13.4 offline: CallArgument(value=None).to_json() =", cdp.runtime.CallArgument(value=None).to_json())
async def main():
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p id=b>hello</p>")
        conn = browser.connection
        for label, filt in [("typed", TargetFilter([FilterEntry(type_="page")])), ("dict workaround", TargetFilter([{"type": "page"}]))]:
            try:
                res = await asyncio.wait_for(conn.send(cdp.target.get_targets(filter_=filt)), 15)
                print(f"A13.1 chrome {label}: OK types={[t.type_ for t in res]}")
            except Exception as e:
                print(f"A13.1 chrome {label}: {type(e).__name__}: {e}")
        el = await tab.select("#b")
        print("A13.3 chrome: str(el.backend_node_id) =", repr(str(el.backend_node_id)))
        wid, _ = await tab.get_window(); print("A13.3 chrome: f'{wid}' =", repr(f"{wid}"))
        doc = await tab.send(cdp.runtime.evaluate("document", return_by_value=False))
        oid = doc[0].object_id
        fn = 'function(x){return arguments.length+":"+(x===null?"null":typeof x)}'
        for label, arg in [("value=None", cdp.runtime.CallArgument(value=None)), ("value=0", cdp.runtime.CallArgument(value=0)),
                           ("unserializable 'null'", cdp.runtime.CallArgument(unserializable_value=cdp.runtime.UnserializableValue("null")))]:
            r, exc = await asyncio.wait_for(tab.send(cdp.runtime.call_function_on(fn, object_id=oid, arguments=[arg], return_by_value=True)), 15)
            print(f"A13.4 chrome {label}: {r.value!r} exc={exc}")
        # what about passing None inside a list/object value? (json null representable via container)
        r, exc = await tab.send(cdp.runtime.call_function_on('function(x){return x[0]===null}', object_id=oid, arguments=[cdp.runtime.CallArgument(value=[None])], return_by_value=True))
        print("A13.4 chrome value=[None] -> x[0]===null:", r.value)
        # evaluate alternative
        r, exc = await tab.send(cdp.runtime.evaluate("null", return_by_value=True))
        print("A13.4 chrome evaluate('null') RemoteObject:", r.type_, r.subtype, r.value)
    finally:
        await browser.stop()
asyncio.run(asyncio.wait_for(main(), 90))
