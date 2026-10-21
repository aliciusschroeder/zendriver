import asyncio
import contextlib
import io
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import zendriver as zd  # noqa: E402
from probe_common import serve  # noqa: E402

print("zendriver from", zd.__file__, "python", sys.version.split()[0])


async def step(name, coro):
    try:
        r = await asyncio.wait_for(coro, 20)
        print(f"[{name}] ->", repr(r)[:300])
        return r
    except Exception as e:
        print(f"[{name}] EXC {type(e).__name__}: {e}"[:300])
        return None


async def main() -> None:
    srv, port = serve()
    browser = await zd.start(headless=True)
    try:
        tab = await browser.get(f"http://127.0.0.1:{port}/main")
        await tab.wait_for_ready_state("complete")
        await asyncio.sleep(1.0)
        # A5.4 proper
        din = await tab.select("div#inner", include_frames=True)
        print("A5.4 din:", din, "children:", din.children)
        print("A5.4 node_id before:", din.node_id)
        await din.update()
        print("A5.4 node_id after update:", din.node_id)
        await step("A5.4 din.query_selector_all b", din.query_selector_all("b"))
        await step("A5.4 din.query_selector b", din.query_selector("b"))
        # A5.6 print + concurrent
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = await asyncio.gather(
                *(tab.select_all("div", include_frames=True) for _ in range(6))
            )
        print("A5.6 lens concurrent:", [len(r) for r in res])
        print("A5.6 stdout lines:", buf.getvalue().count("Exception in new content doc ids loop"))
        seq = await tab.select_all("div", include_frames=True)
        print("A5.6 sequential len:", len(seq))

        # R36
        tab = await browser.get(f"http://127.0.0.1:{port}/text")
        await tab.wait_for_ready_state("complete")
        r = await step("A6.4 find_all Login", tab.find_all("Login"))
        print("   ", [(e.tag, e.backend_node_id) for e in r or []])
        r = await step("A6.4 find_all needle", tab.find_all("needle"))
        print("   ", [(e.tag, e.backend_node_id) for e in r or []])
        r = await step(
            "A6.10 tag_hint=a", tab.find_elements_by_text("needle", tag_hint="a")
        )
        print("    tags:", [e.tag for e in r or []])
        r = await step(
            "A5.10 find return_enclosing_element=False",
            tab.find("top paragraph", return_enclosing_element=False),
        )
        if r is not None:
            print("    node_type:", r.node_type, r.node_name)

        # R37
        tab = await browser.get(f"http://127.0.0.1:{port}/rows")
        await tab.wait_for_ready_state("complete")
        rows = await tab.select_all("tr")
        print("R37 rows:", len(rows))
        for attempt in range(3):
            res = await asyncio.gather(*(r.query_selector("td") for r in rows))
            print("R37 row.query_selector None count:", sum(x is None for x in res), "of", len(res),
                  "__last leftovers:", sum(1 for r in rows if getattr(r, "__last", None)))
        res = await asyncio.gather(*(tab.query_selector("#topp") for _ in range(10)))
        print("R37 10x tab.query_selector None:", sum(x is None for x in res))
        res = await asyncio.gather(*(tab.query_selector_all("p") for _ in range(10)))
        print("R37 10x tab.query_selector_all lens:", [len(x) for x in res])
        res = await asyncio.gather(*(tab.select("#topp", timeout=2) for _ in range(10)), return_exceptions=True)
        print("R37 10x tab.select:", [type(x).__name__ for x in res])
    finally:
        await browser.stop()
        srv.shutdown()


asyncio.run(main())
