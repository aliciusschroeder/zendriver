import asyncio, traceback
import zendriver as zd
from zendriver import cdp
from zendriver.core.browser import Browser
from zendriver.core.config import Config

def ti(tid, type_="page", url="about:blank"):
    return cdp.target.TargetInfo(target_id=cdp.target.TargetID(tid), type_=type_, title="t", url=url, attached=False, can_access_opener=False)

async def main():
    b = Browser(Config(browser_executable_path="/bin/true"))
    # 1. empty browser
    try:
        print("next(iter(empty), None) ->", next(iter(b), None))
    except Exception as e:
        print("1 empty:", type(e).__name__, e)
    try:
        print("list(empty) ->", list(b))
    except Exception as e:
        print("1b list empty:", type(e).__name__, e)
    # 2. only non-page target
    b.targets = [b._create_tab(ti("sw1", "service_worker"))]
    try:
        print("list(only sw) ->", list(b))
    except Exception as e:
        print("2 only sw:", type(e).__name__, e)
    # 3. nested iteration
    b.targets = [b._create_tab(ti("A")), b._create_tab(ti("B"))]
    try:
        pairs = [(x.target_id, y.target_id) for x in b for y in b]
        print("nested ->", pairs)
    except Exception as e:
        print("3 nested:", type(e).__name__, e)
    # 4. exhausted iterator called again
    it = iter(b)
    print("list(it):", [t.target_id for t in it])
    try:
        print("next(it, None) after exhaustion ->", next(it, None))
    except Exception as e:
        print("4 after exhaustion:", type(e).__name__, e)
    # 5. zip
    try:
        print("zip:", [(x.target_id, y.target_id) for x, y in zip(b, b)])
    except Exception as e:
        print("5 zip:", type(e).__name__, e)
    # 6. reversed
    try:
        print("next(reversed(b)):", next(reversed(b)))
    except Exception as e:
        print("6 reversed:", type(e).__name__, e)
    # 7. break then iterate again with tabs: fine?
    for t in b:
        break
    print("after break, list:", [t.target_id for t in b])

asyncio.run(main())
