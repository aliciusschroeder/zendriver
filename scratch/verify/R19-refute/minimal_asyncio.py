import asyncio, sys
async def send(): return 1
def handler():
    try:
        asyncio.ensure_future(send())
        return "ok"
    except RuntimeError as e:
        return f"RuntimeError: {e}"
async def main():
    print(sys.version.split()[0], "ensure_future in to_thread ->", await asyncio.to_thread(handler))
asyncio.run(main())
