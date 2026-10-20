import asyncio, sys
sys.path.insert(0, sys.argv[1])
import test_q12_cancellation as t
async def main():
    tab = t.BusyPageTab()
    el = t._element(tab)
    try:
        await asyncio.wait_for(el.flash(), 1)
    except BaseException as e:
        import traceback; traceback.print_exc()
asyncio.run(main())
