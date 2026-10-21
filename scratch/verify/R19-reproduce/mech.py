import asyncio, sys
async def coro(): return 1
def in_thread():
    try:
        asyncio.ensure_future(coro())
        return "ok"
    except RuntimeError as e:
        return f"RuntimeError: {e}"
async def main():
    print(sys.version.split()[0], await asyncio.to_thread(in_thread))
asyncio.run(main())
