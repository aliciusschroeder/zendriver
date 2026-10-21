import asyncio, sys, json
import zendriver
from zendriver import cdp
print("zendriver from", zendriver.__file__, "python", sys.version.split()[0])
T = cdp.target

def offline():
    # A13.3
    n = cdp.dom.NodeId(5)
    print(f"A13.3 str(NodeId(5))={str(n)!r} f'{{}}'={f'{n}'!r} %s={'%s' % n!r} json={json.dumps(n)} int(str(n)) ->", end=" ")
    try: print(int(str(n)))
    except ValueError as e: print("ValueError", e)
    t = cdp.network.MonotonicTime(1.5)
    print(f"A13.3 f'{{MonotonicTime(1.5)}}'={f'{t}'!r}  str(FrameId('abc'))={str(cdp.page.FrameId('abc'))!r}")
    # A13.1 offline
    tf = T.TargetFilter([T.FilterEntry(type_="page")])
    print("A13.1 TargetFilter.to_json() ->", tf.to_json(), "elem type", type(tf.to_json()[0]).__name__)
    try:
        json.dumps(tf.to_json()); print("A13.1 json.dumps OK")
    except TypeError as e:
        print("A13.1 json.dumps ->", type(e).__name__, e)
    print("A13.1 TargetFilter.from_json([{'type':'page'}])[0] type:", type(T.TargetFilter.from_json([{"type": "page"}])[0]).__name__)
    print("A13.1 ArrayOfStrings.from_json([1])[0] isinstance StringIndex:",
          isinstance(cdp.dom_snapshot.ArrayOfStrings.from_json([1])[0], cdp.dom_snapshot.StringIndex))
    # A13.4 offline
    print("A13.4 CallArgument(value=None).to_json() ->", cdp.runtime.CallArgument(value=None).to_json())

async def online():
    browser = await zendriver.start(headless=True)
    try:
        tab = await browser.get("data:text/html,<p id=b>x</p>")
        # A13.1
        for name, filt in (("typed", T.TargetFilter([T.FilterEntry(type_="page")])),
                           ("dict workaround", T.TargetFilter([{"type": "page"}]))):
            try:
                infos = await asyncio.wait_for(browser.connection.send(T.get_targets(filter_=filt)), 20)
                print(f"A13.1 {name}: get_targets OK types={sorted({i.type_ for i in infos})}")
            except Exception as e:
                print(f"A13.1 {name}: get_targets RAISED {type(e).__name__}: {e}")
        try:
            await asyncio.wait_for(browser.connection.send(T.set_discover_targets(True, filter_=T.TargetFilter([T.FilterEntry(type_="page")]))), 20)
            print("A13.1 typed set_discover_targets OK")
        except Exception as e:
            print(f"A13.1 typed set_discover_targets RAISED {type(e).__name__}: {e}")
        # A13.3 with a real element id
        el = await tab.select("#b")
        print(f"A13.3 real: str(el.backend_node_id)={str(el.backend_node_id)!r}")
        # A13.4
        obj = await tab.send(cdp.runtime.evaluate("document"))
        fn = "function(x){return arguments.length + ':' + (x === null ? 'null' : typeof x)}"
        for label, arg in (("value=None", cdp.runtime.CallArgument(value=None)),
                           ("value=0", cdp.runtime.CallArgument(value=0)),
                           ("unserializable 'null'", cdp.runtime.CallArgument(unserializable_value=cdp.runtime.UnserializableValue("null")))):
            res, exc = await tab.send(cdp.runtime.call_function_on(fn, object_id=obj[0].object_id, arguments=[arg], return_by_value=True))
            print(f"A13.4 {label} -> {res.value} {exc or ''}")
    finally:
        await browser.stop()

offline()
asyncio.run(asyncio.wait_for(online(), 90))
