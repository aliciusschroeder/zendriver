from __future__ import annotations

import asyncio
import contextlib
import functools
from typing import Any, AsyncIterator, Awaitable, Callable, Concatenate, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")


@contextlib.asynccontextmanager
async def dom_lock(tab: Any) -> AsyncIterator[None]:
    """
    serialise DOM queries on one tab: every DOM.getDocument discards the node ids
    that other queries on the same tab are still using.
    re-entrant for the task that holds it (retries call update() and themselves).
    """
    state = vars(tab)
    task = asyncio.current_task()
    if state.get("_dom_lock_owner") is task:
        yield
        return
    lock = state.get("_dom_lock")
    if lock is None:
        lock = state["_dom_lock"] = asyncio.Lock()
    async with lock:
        state["_dom_lock_owner"] = task
        try:
            yield
        finally:
            state["_dom_lock_owner"] = None


def dom_locked(
    func: Callable[Concatenate[Any, _P], Awaitable[_R]],
) -> Callable[Concatenate[Any, _P], Awaitable[_R]]:
    @functools.wraps(func)
    async def wrapper(self: Any, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        from .element import Element

        tab = self._tab if isinstance(self, Element) else self
        async with dom_lock(tab):
            return await func(self, *args, **kwargs)

    return wrapper
