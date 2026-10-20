import asyncio
import zendriver as zd
from zendriver import cdp
R = cdp.runtime
async def main():
    b = await zd.start(headless=True)
    tab = await b.get("about:blank")
    win, _ = await tab.send(R.evaluate("window"))
    fn = "function(x){ return arguments.length + ':' + (x === null ? 'null' : typeof x); }"
    print("CallArgument(value=None).to_json() ->", R.CallArgument(value=None).to_json())
    for label, arg in [("value=None", R.CallArgument(value=None)), ("value=0", R.CallArgument(value=0)), ("value=''", R.CallArgument(value=""))]:
        res, exc = await asyncio.wait_for(tab.send(R.call_function_on(fn, object_id=win.object_id, arguments=[arg], return_by_value=True)), 10)
        print(label, "->", res.value)
    try:
        res, exc = await tab.send(R.call_function_on(fn, object_id=win.object_id, arguments=[R.CallArgument(unserializable_value=R.UnserializableValue("null"))], return_by_value=True))
        print("unserializable null ->", res.value, exc)
    except Exception as e:
        print("unserializable null ERR", str(e)[:120])
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
