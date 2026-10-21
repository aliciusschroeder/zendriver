"""edge cases of zendriver.core.tab._wait_for compared with asyncio.wait_for"""

import asyncio
import gc
import sys

from zendriver.core.tab import _wait_for

ver = sys.version_info
errors: list[str] = []


def handler(loop, ctx):  # noqa
    errors.append(str(ctx.get("message")) + " " + repr(ctx.get("exception")))


async def outcome(coro_factory, impl):
    try:
        r = await coro_factory(impl)
        return f"returned {r!r}"
    except asyncio.CancelledError as e:
        return f"CancelledError{e.args}"
    except BaseException as e:  # noqa
        return f"{type(e).__name__}({e})"


async def case_same_iteration(impl):
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    async def inner():
        return await fut

    t = asyncio.create_task(impl(inner(), 5))
    await asyncio.sleep(0.01)
    fut.set_result("EL")
    t.cancel("watchdog")
    await asyncio.wait({t}, timeout=2)
    if t.cancelled():
        return "cancelled"
    return "LOST: " + repr(t.exception() or t.result())


async def case_swallow_then_return(impl):
    async def inner():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            return "swallowed"

    return await impl(inner(), 0.05)


async def case_raise_on_cancel_timeout(impl):
    async def inner():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise ValueError("cleanup failed")

    return await impl(inner(), 0.05)


async def case_raise_on_cancel_by_caller(impl):
    started = asyncio.Event()

    async def inner():
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            raise ValueError("cleanup failed")

    t = asyncio.create_task(impl(inner(), 5))
    await started.wait()
    t.cancel()
    await asyncio.wait({t}, timeout=2)
    if t.cancelled():
        return "cancelled"
    return "outer got " + repr(t.exception() or t.result())


async def case_outer_asyncio_timeout(impl):
    if ver < (3, 11):
        return "n/a"

    async def inner():
        await asyncio.sleep(10)

    task = asyncio.current_task()
    try:
        async with asyncio.timeout(0.05):
            await impl(inner(), 5)
    except TimeoutError:
        return f"TimeoutError, cancelling()={task.cancelling()}"
    return "no timeout"


async def case_outer_wait_for(impl):
    async def inner():
        await asyncio.sleep(10)

    try:
        await asyncio.wait_for(impl(inner(), 5), 0.05)
    except asyncio.TimeoutError:
        return "TimeoutError"
    return "no timeout"


async def case_double_cancel(impl):
    started = asyncio.Event()
    finished = asyncio.Event()

    async def inner():
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            await asyncio.sleep(0.1)  # slow cleanup
            finished.set()
            raise RuntimeError("slow cleanup failed")

    t = asyncio.create_task(impl(inner(), 5))
    await started.wait()
    t.cancel()
    await asyncio.sleep(0.01)
    t.cancel()
    await asyncio.wait({t}, timeout=2)
    await asyncio.wait_for(finished.wait(), 2)
    await asyncio.sleep(0.01)
    return f"cancelled={t.cancelled()} inner_finished={finished.is_set()}"


async def case_inner_raises(impl):
    exc = KeyError("k")

    async def inner():
        await asyncio.sleep(0)
        raise exc

    try:
        await impl(inner(), 5)
    except KeyError as e:
        return f"same object: {e is exc}"


async def case_inner_cancelled_by_other(impl):
    # the inner awaits a future that somebody else cancels
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    async def inner():
        return await fut

    loop.call_later(0.01, fut.cancel)
    return await impl(inner(), 5)


async def case_timeout_answer_same_iteration(impl):
    # the inner's answer and the timeout land in the same iteration
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    async def inner():
        return await fut

    loop.call_later(0.05, fut.set_result, "EL")
    return await impl(inner(), 0.05)


async def main():
    asyncio.get_running_loop().set_exception_handler(handler)
    print("python", sys.version.split()[0])
    cases = [
        case_same_iteration,
        case_swallow_then_return,
        case_raise_on_cancel_timeout,
        case_raise_on_cancel_by_caller,
        case_outer_asyncio_timeout,
        case_outer_wait_for,
        case_double_cancel,
        case_inner_raises,
        case_inner_cancelled_by_other,
        case_timeout_answer_same_iteration,
    ]
    for c in cases:
        for name, impl in (("wait_for", asyncio.wait_for), ("_wait_for", _wait_for)):
            r = await outcome(c, impl)
            gc.collect()
            await asyncio.sleep(0.02)
            gc.collect()
            left = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            print(f"  {c.__name__:38s} {name:10s} -> {r}  leftover={len(left)} logged={errors}")
            errors.clear()


asyncio.run(main())
