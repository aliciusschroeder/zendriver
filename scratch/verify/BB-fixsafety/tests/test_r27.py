import asyncio
import importlib
import pkgutil
import re

import pytest

import zendriver
from zendriver import cdp
from zendriver.core import util
from zendriver.core.connection import Connection

from fakepeer import FakePeer

print("ZENDRIVER IMPORTED FROM", zendriver.__file__)


def _domains() -> dict[str, str]:
    out = {}
    for m in pkgutil.iter_modules(cdp.__path__):
        if m.name == "util":
            continue
        mod = importlib.import_module(f"zendriver.cdp.{m.name}")
        with open(mod.__file__) as f:  # type: ignore[arg-type]
            for d in set(re.findall(r'"method": "([A-Za-z]+)\.', f.read())):
                out[d] = mod.__name__
    return out


@pytest.mark.parametrize("domain,module", sorted(_domains().items()))
def test_cdp_get_module_maps_every_domain(domain: str, module: str) -> None:
    assert util.cdp_get_module(domain.lower()).__name__ == module


@pytest.mark.parametrize(
    "enable,event",
    [
        (lambda: cdp.web_authn.enable(enable_ui=True), cdp.web_authn.CredentialAdded),
        (
            lambda: cdp.fed_cm.enable(disable_rejection_delay=True),
            cdp.fed_cm.DialogShown,
        ),
    ],
)
async def test_manual_multiword_enable_is_tracked(enable, event) -> None:  # type: ignore[no-untyped-def]
    peer = FakePeer()
    conn = Connection(await peer.start())
    try:
        await asyncio.wait_for(conn.send(enable()), 5)
        mod = util.cdp_get_module(event.__module__)
        print("manually_enabled_domains:", [m.__name__ for m in conn.manually_enabled_domains])
        conn.add_handler(event, lambda e: None)
        mark = len(peer.received)
        await asyncio.wait_for(conn.send(cdp.page.reload()), 5)
        after = [(m["method"], m.get("params")) for m in peer.received[mark:]]
        print("sent after adding handler:", after)
        assert mod in conn.manually_enabled_domains
        assert after == [("Page.reload", {})], after
    finally:
        await conn.aclose()
        await peer.stop()
