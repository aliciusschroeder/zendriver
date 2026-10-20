"""Browser-free: check which wait_for parameter receives the values passed to Tab.__call__."""
import asyncio
import inspect

import zendriver
from zendriver import cdp
from zendriver.core.tab import Tab

print("zendriver from:", zendriver.__file__)

calls = []


async def main() -> None:
    ti = cdp.target.TargetInfo(
        target_id=cdp.target.TargetID("T1"),
        type_="page",
        title="t",
        url="about:blank",
        attached=True,
        can_access_opener=False,
    )
    tab = Tab("ws://127.0.0.1:1/devtools/page/T1", ti, None)

    real_sig = inspect.signature(Tab.wait_for)

    async def fake_wait_for(*args, **kwargs):
        # bind against the real signature (minus self) to see which parameter got what
        bound = real_sig.bind(tab, *args, **kwargs)
        bound.apply_defaults()
        d = dict(bound.arguments)
        d.pop("self")
        calls.append((args, kwargs, d))
        return d

    tab.wait_for = fake_wait_for  # instance attribute, allowed by CantTouchThis

    for label, coro in [
        ("tab(text='Hello needle')", tab(text="Hello needle")),
        ("tab('Hello needle')", tab("Hello needle")),
        ("tab(selector='#p1')", tab(selector="#p1")),
        ("tab(text='X', timeout=3)", tab(text="X", timeout=3)),
    ]:
        d = await coro
        print(f"{label:30s} raw={calls[-1][0]} kw={calls[-1][1]} -> wait_for bound {d}")


asyncio.run(main())
