import gc
import os
import pathlib
import zipfile

import zendriver
from zendriver import cdp
from zendriver.core import util
from zendriver.core.config import Config


def test_print_origin() -> None:
    print("zendriver imported from", zendriver.__file__)


def test_circle_keeps_y_zero() -> None:
    at_zero = list(util.circle(100, 0, radius=10, num=4))
    at_hundred = list(util.circle(100, 100, radius=10, num=4))
    assert at_zero != at_hundred
    # y=0 must be treated like any other y, i.e. shifted by -100 relative to y=100
    for (x0, y0), (x1, y1) in zip(at_zero, at_hundred):
        assert x0 == x1
        assert y1 - y0 == 100
    # omitting y still means y = x
    assert list(util.circle(100, radius=10, num=4)) == at_hundred


def _node(bid: int, name: str, children=None) -> cdp.dom.Node:
    return cdp.dom.Node(
        node_id=cdp.dom.NodeId(bid),
        backend_node_id=cdp.dom.BackendNodeId(bid),
        node_type=1,
        node_name=name.upper(),
        local_name=name,
        node_value="",
        children=children,
    )


class FakeTab:
    """answers DOM.getOuterHTML from a fixed table, like the browser would"""

    def __init__(self, html: dict[int, str]):
        self.html = html

    async def send(self, cmd):
        request = next(cmd)
        assert request["method"] == "DOM.getOuterHTML"
        try:
            cmd.send({"outerHTML": self.html[request["params"]["backendNodeId"]]})
        except StopIteration as e:
            return e.value
        raise AssertionError("command did not finish")


async def test_html_from_tree_emits_each_node_once() -> None:
    p = _node(5, "p")
    body = _node(4, "body", [p])
    head = _node(3, "head")
    html = _node(2, "html", [head, body])
    doc = _node(1, "#document", [html])
    tab = FakeTab(
        {
            2: "<html><head></head><body><p>hello</p></body></html>",
            3: "<head></head>",
            4: "<body><p>hello</p></body>",
            5: "<p>hello</p>",
        }
    )
    out = await util.html_from_tree(doc, tab)  # type: ignore[arg-type]
    assert out == "<html><head></head><body><p>hello</p></body></html>"


def _config() -> Config:
    return Config(browser_executable_path="/bin/true", headless=True)


def test_add_extension_dir_uses_root_manifest(tmp_path: pathlib.Path) -> None:
    (tmp_path / "manifest.json").write_text("{}")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "manifest.webmanifest").write_text("{}")
    (tmp_path / "assets" / "page").mkdir(parents=True)
    (tmp_path / "assets" / "page" / "manifest.json").write_text("{}")
    config = _config()
    config.add_extension(tmp_path)
    assert [pathlib.Path(p) for p in config._extensions] == [tmp_path]


def test_add_extension_dir_finds_nested_extension(tmp_path: pathlib.Path) -> None:
    ext = tmp_path / "unpacked" / "ext"
    (ext / "deeper").mkdir(parents=True)
    (ext / "manifest.json").write_text("{}")
    (ext / "deeper" / "manifest.json").write_text("{}")
    config = _config()
    config.add_extension(tmp_path)
    assert [pathlib.Path(p) for p in config._extensions] == [ext]


def test_add_extension_crx_dir_is_removed(tmp_path: pathlib.Path) -> None:
    crx = tmp_path / "ext.crx"
    with zipfile.ZipFile(crx, "w") as z:
        z.writestr("manifest.json", "{}")
    config = _config()
    config.add_extension(crx)
    extracted = str(config._extensions[0])
    try:
        assert os.path.isfile(os.path.join(extracted, "manifest.json"))
        del config
        gc.collect()
        assert not os.path.exists(extracted)
    finally:
        import shutil

        shutil.rmtree(extracted, ignore_errors=True)
