import asyncio, json
import zendriver as zd
async def main():
    b = await zd.start(headless=True)
    tab = await b.get("data:text/html,<button id=b>x</button>")
    el = await tab.select("#b")
    wid, bounds = await tab.get_window()
    print("str(el.backend_node_id) =", str(el.backend_node_id), "| f'{wid}' =", f"{wid}", "| json:", json.dumps({"w": wid}))
    try: int(str(el.backend_node_id))
    except Exception as e: print("int(str(id)) ->", type(e).__name__, e)
    await b.stop()
asyncio.run(asyncio.wait_for(main(), 60))
