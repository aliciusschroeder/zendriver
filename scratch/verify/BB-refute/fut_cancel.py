import asyncio, sys
async def main():
    f = asyncio.get_running_loop().create_future()
    async def value():
        return await f
    try:
        await asyncio.wait_for(value(), 0.2)
    except asyncio.TimeoutError:
        pass
    print(sys.version.split()[0], "shared future after timed-out wait_for:", "cancelled" if f.cancelled() else "pending")
asyncio.run(main())
