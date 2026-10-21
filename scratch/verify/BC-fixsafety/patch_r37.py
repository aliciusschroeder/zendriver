import pathlib, shutil, sys
root = pathlib.Path(sys.argv[1]) / "zendriver/core"
shutil.copy(pathlib.Path(__file__).parent / "domlock_module.py", root / "_domlock.py")

def patch(path, pairs):
    s = path.read_text()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old)
        s = s.replace(old, new)
    path.write_text(s)

patch(root / "tab.py", [
    ("from . import element, util\n", "from . import element, util\nfrom ._domlock import dom_locked\n"),
    ("    async def query_selector_all(\n        self,\n        selector: str,\n        _node:",
     "    @dom_locked\n    async def query_selector_all(\n        self,\n        selector: str,\n        _node:"),
    ("    async def query_selector(\n        self,\n        selector: str,\n        _node:",
     "    @dom_locked\n    async def query_selector(\n        self,\n        selector: str,\n        _node:"),
    ("    async def find_elements_by_text(\n", "    @dom_locked\n    async def find_elements_by_text(\n"),
    # __last must not outlive the retry
    ('''                    setattr(_node, "__last", True)
                    return await self.query_selector_all(
                        selector, _node, _include_frames=_include_frames
                    )''', '''                    setattr(_node, "__last", True)
                    try:
                        return await self.query_selector_all(
                            selector, _node, _include_frames=_include_frames
                        )
                    finally:
                        vars(_node).pop("__last", None)'''),
    ('''                    setattr(_node, "__last", True)
                    return await self.query_selector(selector, _node)''', '''                    setattr(_node, "__last", True)
                    try:
                        return await self.query_selector(selector, _node)
                    finally:
                        vars(_node).pop("__last", None)'''),
])
patch(root / "element.py", [
    ("from . import util\n", "from . import util\nfrom ._domlock import dom_locked\n"),
    ("    async def remove_from_dom(self) -> None:\n", "    @dom_locked\n    async def remove_from_dom(self) -> None:\n"),
    ("    async def update(self, _node: cdp.dom.Node | None = None) -> Element:\n",
     "    @dom_locked\n    async def update(self, _node: cdp.dom.Node | None = None) -> Element:\n"),
    ("    async def query_selector_all(self, selector: str) -> list[Element]:\n",
     "    @dom_locked\n    async def query_selector_all(self, selector: str) -> list[Element]:\n"),
    ("    async def query_selector(self, selector: str) -> Element | None:\n",
     "    @dom_locked\n    async def query_selector(self, selector: str) -> Element | None:\n"),
])
print("patched", root)
