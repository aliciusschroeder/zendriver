import asyncio
import zendriver as zd
from zendriver import cdp
T = cdp.target
async def main():
    b = await zd.start(headless=True)
    tab = b.main_tab
    flt = T.TargetFilter([T.FilterEntry(type_="page")])
    print("to_json ->", flt.to_json(), type(flt.to_json()[0]).__name__)
    for name, mk in [("get_targets", lambda f: T.get_targets(filter_=f)),
                     ("set_discover_targets", lambda f: T.set_discover_targets(True, filter_=f))]:
        try:
            r = await asyncio.wait_for(b.connection.send(mk(flt)), 10)
            print("typed OK", name, r if not isinstance(r, list) else len(r))
        except Exception as e:
            print("typed ERR", name, type(e).__name__, e)
    # wire-format dicts smuggled in work
    r = await asyncio.wait_for(b.connection.send(T.get_targets(filter_=T.TargetFilter([{"type": "page"}]))), 10)
    print("dict workaround OK:", [t.type_ for t in r])
    # from_json leaves dicts, not FilterEntry
    print("from_json elem type:", type(T.TargetFilter.from_json([{"type":"page"}])[0]).__name__)
    from zendriver.cdp import dom_snapshot as ds
    a = ds.ArrayOfStrings.from_json([1,2])
    print("ArrayOfStrings elem is StringIndex:", isinstance(a[0], ds.StringIndex))
    print("mapper size:", len(b.connection.mapper))
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
